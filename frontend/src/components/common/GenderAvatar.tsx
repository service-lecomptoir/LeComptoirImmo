import { useMemo } from 'react'
import { Building2 } from 'lucide-react'
import { createAvatar } from '@dicebear/core'
import { avataaars } from '@dicebear/collection'
import type { Civility } from '@/types/tenant'

/**
 * Avatar illustré (style « avataaars ») généré de façon déterministe à partir du
 * nom : chaque personne garde le même visage. La civilité oriente le rendu
 * (coiffures longues / pas de barbe pour Mme, coiffures courtes pour M.).
 * Société : icône immeuble. Purement décoratif.
 */
const WOMEN_TOP = [
  'bob', 'bun', 'curly', 'curvy', 'longButNotTooLong', 'miaWallace',
  'straight01', 'straight02', 'straightAndStrand', 'bigHair', 'shaggy', 'frida',
]
const MEN_TOP = [
  'shortFlat', 'shortRound', 'shortCurly', 'shortWaved', 'theCaesar',
  'theCaesarAndSidePart', 'sides', 'shavedSides', 'dreads01', 'frizzle',
]

export function GenderAvatar({
  civility,
  isCompany = false,
  size = 40,
  seed,
}: {
  civility?: Civility | null
  isCompany?: boolean
  size?: number
  seed?: string | null
}) {
  const isF = !isCompany && civility === 'Mme'
  const isM = !isCompany && civility === 'M'
  const bg = isCompany ? 'bg-amber-100' : isF ? 'bg-pink-100' : isM ? 'bg-blue-100' : 'bg-gray-100'

  const dataUri = useMemo(() => {
    if (isCompany) return null
    const s = (seed && seed.trim()) || (isF ? 'Madame' : isM ? 'Monsieur' : 'Locataire')
    const opts: Record<string, unknown> = {
      seed: s,
      radius: 50,
      accessoriesProbability: 0,
      // Traits neutres / professionnels (pas d'yeux en cœur, pas de t-shirt à motif).
      eyes: ['default', 'happy', 'wink', 'side', 'squint'],
      eyebrows: ['default', 'defaultNatural', 'flatNatural', 'raisedExcited'],
      mouth: ['default', 'smile', 'twinkle', 'serious'],
      clothing: ['blazerAndShirt', 'blazerAndSweater', 'collarAndSweater', 'shirtCrewNeck', 'shirtVNeck'],
    }
    if (isF) { opts.top = WOMEN_TOP; opts.facialHairProbability = 0 }
    else if (isM) { opts.top = MEN_TOP; opts.facialHairProbability = 25 }
    return createAvatar(avataaars, opts).toDataUri()
  }, [isCompany, isF, isM, seed])

  return (
    <div
      className={`rounded-full ${bg} flex items-center justify-center shrink-0 overflow-hidden`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {isCompany || !dataUri ? (
        <Building2 size={Math.round(size * 0.6)} className="text-amber-700" />
      ) : (
        <img src={dataUri} width={size} height={size} alt="" />
      )}
    </div>
  )
}
