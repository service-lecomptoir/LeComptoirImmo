import type { ElementType, ReactNode } from 'react'

interface EmptyStateProps {
  icon: ElementType
  title: string
  hint?: string
  action?: ReactNode
}

/** État vide unifié : icône, titre, indice optionnel et action optionnelle. */
export function EmptyState({ icon: Icon, title, hint, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
        <Icon size={26} className="text-gray-400" />
      </div>
      <p className="text-sm font-medium text-gray-700">{title}</p>
      {hint && <p className="text-xs text-gray-400 mt-1 max-w-xs">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
