import { List, LayoutGrid } from 'lucide-react'

export type ViewMode = 'list' | 'grid'

interface ViewToggleProps {
  value: ViewMode
  onChange: (v: ViewMode) => void
  className?: string
}

/** Sélecteur Liste / Mosaïque (deux boutons icônes). */
export function ViewToggle({ value, onChange, className = '' }: ViewToggleProps) {
  return (
    <div className={`inline-flex items-center rounded-lg border border-gray-200 bg-white p-0.5 ${className}`}>
      <button
        type="button"
        onClick={() => onChange('list')}
        aria-pressed={value === 'list'}
        title="Vue liste"
        className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors ${
          value === 'list' ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100'
        }`}
      >
        <List size={16} />
      </button>
      <button
        type="button"
        onClick={() => onChange('grid')}
        aria-pressed={value === 'grid'}
        title="Vue mosaïque"
        className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors ${
          value === 'grid' ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100'
        }`}
      >
        <LayoutGrid size={16} />
      </button>
    </div>
  )
}
