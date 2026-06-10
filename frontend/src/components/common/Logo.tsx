import { useId } from 'react'

/**
 * Marque « Le Comptoir Immo » — immeuble stylisé (même glyphe que le favicon).
 * Le bâtiment est dessiné en `currentColor` et les fenêtres/porte sont détourées
 * via un masque : elles laissent voir le fond, quel qu'il soit (boîte orange,
 * navy, blanche…). Pilotez la couleur avec une classe `text-*`.
 */
export function LogoMark({ size = 24, className = '' }: { size?: number; className?: string }) {
  const id = useId()
  return (
    <svg
      viewBox="0 0 32 32"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Le Comptoir Immo"
      xmlns="http://www.w3.org/2000/svg"
    >
      <mask id={id} maskUnits="userSpaceOnUse" x="0" y="0" width="32" height="32">
        <rect x="9" y="6.5" width="14" height="19" rx="1.2" fill="white" />
        <g fill="black">
          <rect x="11.3" y="9" width="3" height="3" rx="0.5" />
          <rect x="17.7" y="9" width="3" height="3" rx="0.5" />
          <rect x="11.3" y="13.6" width="3" height="3" rx="0.5" />
          <rect x="17.7" y="13.6" width="3" height="3" rx="0.5" />
          <rect x="14" y="19" width="4" height="6.5" rx="0.6" />
        </g>
      </mask>
      <rect x="9" y="6.5" width="14" height="19" rx="1.2" fill="currentColor" mask={`url(#${id})`} />
    </svg>
  )
}
