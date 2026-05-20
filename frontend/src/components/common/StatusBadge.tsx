import clsx from 'clsx'

type Variant = 'green' | 'red' | 'yellow' | 'blue' | 'gray' | 'purple'

const variants: Record<Variant, string> = {
  green:  'bg-green-100 text-green-800',
  red:    'bg-red-100 text-red-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  blue:   'bg-blue-100 text-blue-800',
  gray:   'bg-gray-100 text-gray-700',
  purple: 'bg-purple-100 text-purple-800',
}

interface StatusBadgeProps {
  label: string
  variant: Variant
  dot?: boolean
}

export function StatusBadge({ label, variant, dot = false }: StatusBadgeProps) {
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium', variants[variant])}>
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', {
        'bg-green-500': variant === 'green',
        'bg-red-500': variant === 'red',
        'bg-yellow-500': variant === 'yellow',
        'bg-blue-500': variant === 'blue',
        'bg-gray-400': variant === 'gray',
        'bg-purple-500': variant === 'purple',
      })} />}
      {label}
    </span>
  )
}
