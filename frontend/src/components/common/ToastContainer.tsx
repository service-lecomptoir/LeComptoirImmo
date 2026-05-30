import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'
import { useToastStore, type ToastType } from '../../store/toast'

const STYLES: Record<ToastType, { wrap: string; icon: JSX.Element }> = {
  success: {
    wrap: 'bg-green-50 border-green-200 text-green-800',
    icon: <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0" />,
  },
  error: {
    wrap: 'bg-red-50 border-red-200 text-red-800',
    icon: <AlertCircle className="h-5 w-5 text-red-600 shrink-0" />,
  },
  info: {
    wrap: 'bg-blue-50 border-blue-200 text-blue-800',
    icon: <Info className="h-5 w-5 text-blue-600 shrink-0" />,
  },
}

/**
 * Conteneur global des notifications transitoires (toasts).
 * Monté une seule fois dans App. Lit le store `useToastStore`.
 */
export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  const remove = useToastStore((s) => s.remove)

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-[calc(100%-2rem)] max-w-sm pointer-events-none">
      {toasts.map((t) => {
        const s = STYLES[t.type]
        return (
          <div
            key={t.id}
            role="alert"
            className={`pointer-events-auto flex items-start gap-3 rounded-lg border px-4 py-3 shadow-md text-sm animate-[slideIn_0.15s_ease-out] ${s.wrap}`}
          >
            {s.icon}
            <span className="flex-1 break-words">{t.message}</span>
            <button
              onClick={() => remove(t.id)}
              className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
              aria-label="Fermer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
