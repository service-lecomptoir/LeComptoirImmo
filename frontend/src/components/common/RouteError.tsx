import { useRouteError } from 'react-router-dom'
import { Spinner } from '@/components/ui'

/** Détecte une erreur de chargement de module (chunk obsolète après déploiement). */
function isChunkError(err: unknown): boolean {
  const msg =
    (err as { message?: string })?.message ??
    (typeof err === 'string' ? err : '') ??
    ''
  return /dynamically imported module|Importing a module script failed|error loading dynamically imported module|Failed to fetch/i.test(
    msg,
  )
}

/**
 * errorElement du routeur : si l'erreur vient d'un chunk obsolète (déploiement
 * pendant que l'onglet était ouvert), on recharge proprement (garde-fou 1×/10 s)
 * au lieu d'afficher l'erreur applicative brute. Sinon, écran d'erreur lisible.
 */
export function RouteError() {
  const err = useRouteError()

  if (isChunkError(err)) {
    const KEY = 'chunk-reload-ts'
    const last = Number(sessionStorage.getItem(KEY) || '0')
    if (Date.now() - last > 10000) {
      sessionStorage.setItem(KEY, String(Date.now()))
      window.location.reload()
    }
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-center px-6">
        <Spinner size={32} className="text-blue-600" />
        <p className="text-sm text-gray-500">Mise à jour de l'application… rechargement en cours.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-6">
      <h2 className="text-lg font-semibold text-gray-900">Une erreur est survenue</h2>
      <p className="text-sm text-gray-500 max-w-md">
        Quelque chose s'est mal passé lors de l'affichage de cette page.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="px-5 py-2.5 rounded-xl text-sm font-semibold text-white"
        style={{ background: 'linear-gradient(135deg, #0D2F5C 0%, #1A4A8A 100%)' }}
      >
        Recharger la page
      </button>
    </div>
  )
}
