import clsx from 'clsx'

interface SpinnerProps {
  /** Diamètre en pixels (défaut 16). */
  size?: number
  className?: string
}

/** Indicateur de chargement circulaire. Hérite de la couleur du texte
 *  (`border-current`) pour s'adapter au contexte (bouton plein, lien, etc.). */
export function Spinner({ size = 16, className }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label="Chargement"
      className={clsx('inline-block animate-spin rounded-full border-2 border-current border-t-transparent align-[-2px]', className)}
      style={{ width: size, height: size }}
    />
  )
}
