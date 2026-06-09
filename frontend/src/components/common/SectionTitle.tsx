import type { LucideIcon } from 'lucide-react'

/**
 * En-tête de section de formulaire : petite icône bleue + titre en capitales
 * grises. Style partagé par tous les formulaires (cohérence visuelle).
 */
export function SectionTitle({ icon: Icon, children }: { icon: LucideIcon; children: React.ReactNode }) {
  return (
    <h3 className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
      <Icon size={14} className="text-blue-500" />
      {children}
    </h3>
  )
}
