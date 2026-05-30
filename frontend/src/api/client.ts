import axios from 'axios'
import { toast } from '../store/toast'
import { getErrorMessage } from '../utils/errors'

const API_URL = import.meta.env.VITE_API_URL || ''

export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// ── Message de confirmation auto selon (méthode, url) ─────────────────────────
// Affiche un toast de succès après chaque enregistrement / modification /
// suppression, sans avoir à le coder dans chaque écran.
function successMessage(method?: string, url?: string): string | null {
  const m = (method || '').toLowerCase()
  if (!['post', 'put', 'patch', 'delete'].includes(m)) return null
  const path = (url || '').split('?')[0]

  // ── Messages spécifiques (avant la liste d'exclusions / la table générique) ──
  if (path.includes('/password') || path.includes('reset-password')) {
    return 'Le mot de passe a bien été modifié.'
  }
  if (path.includes('/validate-declaration')) return 'Le paiement a bien été validé.'
  if (path.includes('/refuse-declaration')) return 'La déclaration de paiement a bien été refusée.'
  if (path.includes('/declare')) return 'Votre paiement a bien été déclaré.'
  if (path.includes('/record')) return 'Le paiement a bien été enregistré.'
  if (path.includes('/terminate')) return 'Le contrat a bien été clôturé.'
  if (path.endsWith('/me')) return 'Vos informations ont bien été enregistrées.'

  // ── Actions qui ne sont PAS de simples CRUD (pas de message générique) ───────
  const deny = [
    '/auth', '/login', '/refresh', 'preview', 'generate', '/pdf',
    'upload', 'toggle', 'initialize', 'read-all', '/read',
    'subscription-requests', 'generate-alerts',
  ]
  if (deny.some((d) => path.includes(d))) return null

  const segs = path.split('/').filter(Boolean) // ex. ['tenants'] ou ['tenants','<id>']
  if (segs.length === 0) return null
  const base = segs[0]

  // base : [création, modification, suppression]
  const MAP: Record<string, [string, string, string]> = {
    tenants: ['Le locataire a bien été ajouté.', 'Le locataire a bien été modifié.', 'Le locataire a bien été supprimé.'],
    owners: ['Le propriétaire a bien été ajouté.', 'Le propriétaire a bien été modifié.', 'Le propriétaire a bien été supprimé.'],
    properties: ['Le bien a bien été ajouté.', 'Le bien a bien été modifié.', 'Le bien a bien été supprimé.'],
    leases: ['Le contrat a bien été créé.', 'Le contrat a bien été modifié.', 'Le contrat a bien été supprimé.'],
    contacts: ['Le contact a bien été ajouté.', 'Le contact a bien été modifié.', 'Le contact a bien été supprimé.'],
    entretiens: ['L’entretien a bien été ajouté.', 'L’entretien a bien été modifié.', 'L’entretien a bien été supprimé.'],
    inspections: ['L’état des lieux a bien été ajouté.', 'L’état des lieux a bien été modifié.', 'L’état des lieux a bien été supprimé.'],
    offers: ['L’offre a bien été ajoutée.', 'L’offre a bien été modifiée.', 'L’offre a bien été supprimée.'],
    tickets: ['L’incident a bien été créé.', 'L’incident a bien été modifié.', 'L’incident a bien été supprimé.'],
    users: ['L’utilisateur a bien été ajouté.', 'L’utilisateur a bien été modifié.', 'L’utilisateur a bien été supprimé.'],
    templates: ['Le modèle a bien été ajouté.', 'Le modèle a bien été modifié.', 'Le modèle a bien été supprimé.'],
  }
  const entry = MAP[base]
  if (!entry) return null

  if (m === 'delete') return entry[2]
  if (m === 'post') {
    // Un POST sur une sous-ressource (/base/{id}/action) n'est pas une création.
    if (segs.length > 1) return null
    return entry[0]
  }
  return entry[1] // put / patch
}

// ── Intercepteur requête : injecte le token JWT ────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Intercepteur réponse : confirmation, refresh token, erreurs ───────────────
apiClient.interceptors.response.use(
  (response) => {
    // Message de confirmation automatique sur les mutations réussies.
    const msg = successMessage(response.config?.method, response.config?.url)
    if (msg) toast.success(msg)
    return response
  },
  async (error) => {
    const original = error.config || {}

    // Les endpoints d'authentification gèrent eux-mêmes leurs erreurs : un 401 sur
    // /auth/login = identifiants incorrects (à afficher sur la page), PAS une session
    // expirée. Ne pas rediriger/recharger (sinon perte du message + reset du formulaire).
    const url: string = original.url || ''
    if (url.includes('/auth/login') || url.includes('/auth/refresh')) {
      return Promise.reject(error)
    }

    // Si 401 et pas déjà en retry → essai de refresh
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', data.access_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return apiClient(original)
        } catch {
          // Refresh échoué → déconnexion
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return Promise.reject(error)
        }
      } else {
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    // ── Filet de sécurité : aucune erreur ne doit être silencieuse ─────────────
    // Tout échec restant (mutation OU lecture) remonte un message à l'utilisateur.
    toast.error(getErrorMessage(error))

    return Promise.reject(error)
  },
)

export const api = apiClient // alias rétrocompatible
