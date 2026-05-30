/**
 * Extrait un message d'erreur lisible depuis une erreur axios / FastAPI.
 * Garantit qu'on a TOUJOURS quelque chose à montrer à l'utilisateur
 * (jamais d'échec silencieux).
 */
export function getErrorMessage(
  error: any,
  fallback = 'Une erreur est survenue. Veuillez réessayer.',
): string {
  // Erreur réseau (serveur injoignable, CORS, coupure)
  if (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error') {
    return 'Connexion au serveur impossible. Vérifiez votre connexion puis réessayez.'
  }

  const data = error?.response?.data

  // FastAPI : { detail: "..." }
  if (typeof data?.detail === 'string' && data.detail.trim()) {
    return data.detail
  }

  // FastAPI validation : { detail: [{ loc, msg, type }, ...] }
  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    const parts = data.detail
      .map((e: any) => {
        const field = Array.isArray(e?.loc) ? e.loc[e.loc.length - 1] : undefined
        const msg = e?.msg || ''
        return field && field !== 'body' ? `${field} : ${msg}` : msg
      })
      .filter(Boolean)
    if (parts.length) return parts.join(' · ')
  }

  // Autres formats courants
  if (typeof data?.message === 'string' && data.message.trim()) return data.message
  if (typeof data === 'string' && data.trim()) return data

  // Codes HTTP parlants
  const status = error?.response?.status
  if (status === 403) return "Vous n'avez pas les droits pour effectuer cette action."
  if (status === 404) return 'Élément introuvable.'
  if (status === 413) return 'Fichier trop volumineux.'
  if (status && status >= 500) return 'Erreur interne du serveur. Réessayez dans un instant.'

  return fallback
}
