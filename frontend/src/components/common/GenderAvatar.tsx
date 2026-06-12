import { UserRound, Building2 } from 'lucide-react'
import type { Civility } from '@/types/tenant'

/**
 * Avatar selon le type : société (immeuble), ou personne genrée par la civilité :
 * silhouette « homme » (M.) ou « femme » (Mme), fond coloré ; neutre (UserRound gris)
 * si civilité inconnue/« Autre ». Purement décoratif : n'affecte aucune donnée.
 */
export function GenderAvatar({
  civility,
  isCompany = false,
  size = 40,
}: {
  civility?: Civility | null
  isCompany?: boolean
  size?: number
}) {
  const isF = !isCompany && civility === 'Mme'
  const isM = !isCompany && civility === 'M'
  const bg = isCompany ? 'bg-amber-100' : isF ? 'bg-pink-100' : isM ? 'bg-blue-100' : 'bg-gray-100'
  const fg = isCompany ? 'text-amber-700' : isF ? 'text-pink-600' : isM ? 'text-blue-700' : 'text-gray-500'
  const glyph = Math.round(size * 0.62)

  return (
    <div
      className={`rounded-full ${bg} flex items-center justify-center shrink-0`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {isCompany ? (
        <Building2 size={glyph} className={fg} />
      ) : isF ? (
        <svg viewBox="0 0 24 24" fill="currentColor" width={glyph} height={glyph} className={fg}>
          {/* cheveux : dôme sur la tête + deux mèches descendantes, ouverture pour le visage */}
          <path d="M6 12a6 6 0 0 1 12 0v4h-2.5v-5a3.5 3.5 0 0 0-7 0v5H6z" />
          {/* visage */}
          <circle cx="12" cy="9.5" r="3.3" />
          {/* épaules */}
          <path d="M5 21c0-3.6 3.1-5.8 7-5.8s7 2.2 7 5.8z" />
        </svg>
      ) : isM ? (
        <svg viewBox="0 0 24 24" fill="currentColor" width={glyph} height={glyph} className={fg}>
          {/* tête (cheveux courts) */}
          <circle cx="12" cy="8" r="4" />
          {/* épaules (carrure) */}
          <path d="M4 20.8c0-4 3.6-6.4 8-6.4s8 2.4 8 6.4a.5.5 0 0 1-.5.5H4.5a.5.5 0 0 1-.5-.5z" />
        </svg>
      ) : (
        <UserRound size={glyph} className={fg} />
      )}
    </div>
  )
}
