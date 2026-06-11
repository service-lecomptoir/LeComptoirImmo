import { useMemo } from 'react'
import { groupPhoneDigits, digitsOnly } from '@/utils/format'

export interface Country {
  code: string
  flag: string
  name: string
  dial: string
}

// France et Guyane française en tête (marché principal), puis DOM/TOM et voisins.
export const PHONE_COUNTRIES: Country[] = [
  { code: 'FR', flag: '🇫🇷', name: 'France', dial: '+33' },
  { code: 'GF', flag: '🇬🇫', name: 'Guyane française', dial: '+594' },
  { code: 'GP', flag: '🇬🇵', name: 'Guadeloupe', dial: '+590' },
  { code: 'MQ', flag: '🇲🇶', name: 'Martinique', dial: '+596' },
  { code: 'RE', flag: '🇷🇪', name: 'La Réunion / Mayotte', dial: '+262' },
  { code: 'BE', flag: '🇧🇪', name: 'Belgique', dial: '+32' },
  { code: 'CH', flag: '🇨🇭', name: 'Suisse', dial: '+41' },
  { code: 'LU', flag: '🇱🇺', name: 'Luxembourg', dial: '+352' },
  { code: 'PT', flag: '🇵🇹', name: 'Portugal', dial: '+351' },
  { code: 'ES', flag: '🇪🇸', name: 'Espagne', dial: '+34' },
  { code: 'SR', flag: '🇸🇷', name: 'Suriname', dial: '+597' },
  { code: 'BR', flag: '🇧🇷', name: 'Brésil', dial: '+55' },
]

// Tri par longueur d'indicatif décroissante pour matcher le plus spécifique d'abord.
const DIALS = [...PHONE_COUNTRIES].sort((a, b) => b.dial.length - a.dial.length)

const DEFAULT_DIAL = '+594' // Guyane française par défaut

interface Props {
  value: string
  onChange: (v: string) => void
  inputClassName?: string
  placeholder?: string
  disabled?: boolean
}

/**
 * Saisie de téléphone avec sélecteur d'indicatif pays (drapeau + indicatif).
 * Stocke la valeur sous la forme « +594 694123456 » (indicatif inclus) — utile
 * pour les envois de SMS automatiques.
 */
export function PhoneInput({ value, onChange, inputClassName, placeholder, disabled }: Props) {
  const { dial, local } = useMemo(() => {
    const v = (value || '').trim()
    const match = DIALS.find(c => v.startsWith(c.dial))
    // Avec indicatif : on retire le 0 initial du numéro local (« +594 0694… » → « +594 694… »).
    if (match) return { dial: match.dial, local: digitsOnly(v.slice(match.dial.length)).replace(/^0+/, '') }
    return { dial: DEFAULT_DIAL, local: digitsOnly(v).replace(/^0+/, '') }
  }, [value])

  const emit = (d: string, l: string) => {
    // Stockage = chiffres only, sans 0 initial (l'indicatif est toujours présent).
    const num = digitsOnly(l).replace(/^0+/, '')
    onChange(num ? `${d} ${num}` : '')
  }

  const inp = inputClassName ||
    'flex-1 w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="flex gap-2">
      <select
        value={dial}
        disabled={disabled}
        onChange={e => emit(e.target.value, local)}
        className="px-2 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
        aria-label="Indicatif pays"
      >
        {PHONE_COUNTRIES.map(c => (
          <option key={c.code} value={c.dial}>{c.flag} {c.dial}</option>
        ))}
      </select>
      <input
        type="tel"
        value={groupPhoneDigits(local)}
        disabled={disabled}
        onChange={e => emit(dial, e.target.value)}
        placeholder={placeholder || '06 94 12 34 56'}
        className={inp}
      />
    </div>
  )
}
