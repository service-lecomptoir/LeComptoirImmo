import { Building2, UserRound } from 'lucide-react'
import type { Civility } from '@/types/tenant'

/**
 * Avatar illustré (couleurs peau + cheveux) selon la civilité : homme (M.) ou
 * femme (Mme) ; immeuble pour une société ; icône neutre si civilité inconnue.
 * Purement décoratif : n'affecte aucune donnée.
 */
const SKIN = '#E8B68F'
const HAIR = '#4A3526'
const HAIR_F = '#5A3526'
const SHIRT_M = '#0D2F5C'   // chemise (bleu marine de marque)
const TOP_F = '#C65D7B'     // haut (rose)

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
  const glyph = Math.round(size * 0.72)

  return (
    <div
      className={`rounded-full ${bg} flex items-center justify-center shrink-0 overflow-hidden`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {isCompany ? (
        <Building2 size={Math.round(size * 0.6)} className="text-amber-700" />
      ) : isF ? (
        <svg viewBox="0 0 24 24" width={glyph} height={glyph}>
          {/* cheveux longs (arrière) tombant sur les épaules */}
          <path d="M6 11c0-3.7 2.7-6.6 6-6.6s6 2.9 6 6.6c0 2.5-.3 4.7-1 6.6h-2.3c.6-1.5.9-3.1.9-4.9 0-2.7-1.5-4.2-3.6-4.2S8.4 9.9 8.4 12.6c0 1.8.3 3.4.9 4.9H7c-.7-1.9-1-4.1-1-6.6z" fill={HAIR_F} />
          {/* épaules / haut */}
          <path d="M5 21c0-3.6 3.1-5.7 7-5.7s7 2.1 7 5.7z" fill={TOP_F} />
          {/* cou */}
          <rect x="10.7" y="12.2" width="2.6" height="3.4" rx="1.1" fill={SKIN} />
          {/* visage */}
          <circle cx="12" cy="9.4" r="3.7" fill={SKIN} />
          {/* frange / cheveux avant */}
          <path d="M8.4 8.6C8.4 5.9 10 4.3 12 4.3s3.6 1.6 3.6 4.3c-.6-1.1-1.2-1.7-2-1.9-.4-.8-1.6-1-1.6-1s-1.2.2-1.6 1c-.8.2-1.4.8-2 1.9z" fill={HAIR_F} />
        </svg>
      ) : isM ? (
        <svg viewBox="0 0 24 24" width={glyph} height={glyph}>
          {/* épaules / chemise */}
          <path d="M4 21c0-3.7 3.6-5.9 8-5.9s8 2.2 8 5.9z" fill={SHIRT_M} />
          {/* cou */}
          <rect x="10.6" y="12.4" width="2.8" height="3.4" rx="1.2" fill={SKIN} />
          {/* oreilles */}
          <circle cx="8.1" cy="9.7" r="0.85" fill={SKIN} />
          <circle cx="15.9" cy="9.7" r="0.85" fill={SKIN} />
          {/* visage */}
          <circle cx="12" cy="9.3" r="4" fill={SKIN} />
          {/* cheveux courts */}
          <path d="M7.9 8.9c-.3-3.2 1.7-5.5 4.1-5.5s4.4 2.3 4.1 5.5c-.5-1.1-1-1.7-1.6-2-.2-.9-1.2-1.4-2.5-1.4s-2.3.5-2.5 1.4c-.6.3-1.1.9-1.6 2z" fill={HAIR} />
        </svg>
      ) : (
        <UserRound size={Math.round(size * 0.62)} className="text-gray-500" />
      )}
    </div>
  )
}
