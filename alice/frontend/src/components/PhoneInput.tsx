import { useEffect, useRef, useState } from 'react'

export interface Country {
  iso: string
  name: string
  dial: string
  flag: string
}

/** Indicatifs proposés (marché francophone + principaux pays). dial = indicatif unique. */
export const COUNTRIES: Country[] = [
  { iso: 'FR', name: 'France', dial: '+33', flag: '🇫🇷' },
  { iso: 'BE', name: 'Belgique', dial: '+32', flag: '🇧🇪' },
  { iso: 'CH', name: 'Suisse', dial: '+41', flag: '🇨🇭' },
  { iso: 'LU', name: 'Luxembourg', dial: '+352', flag: '🇱🇺' },
  { iso: 'MC', name: 'Monaco', dial: '+377', flag: '🇲🇨' },
  { iso: 'ES', name: 'Espagne', dial: '+34', flag: '🇪🇸' },
  { iso: 'PT', name: 'Portugal', dial: '+351', flag: '🇵🇹' },
  { iso: 'IT', name: 'Italie', dial: '+39', flag: '🇮🇹' },
  { iso: 'DE', name: 'Allemagne', dial: '+49', flag: '🇩🇪' },
  { iso: 'GB', name: 'Royaume-Uni', dial: '+44', flag: '🇬🇧' },
  { iso: 'NL', name: 'Pays-Bas', dial: '+31', flag: '🇳🇱' },
  { iso: 'IE', name: 'Irlande', dial: '+353', flag: '🇮🇪' },
  { iso: 'US', name: 'États-Unis / Canada', dial: '+1', flag: '🇺🇸' },
  { iso: 'MA', name: 'Maroc', dial: '+212', flag: '🇲🇦' },
  { iso: 'DZ', name: 'Algérie', dial: '+213', flag: '🇩🇿' },
  { iso: 'TN', name: 'Tunisie', dial: '+216', flag: '🇹🇳' },
  { iso: 'SN', name: 'Sénégal', dial: '+221', flag: '🇸🇳' },
  { iso: 'CI', name: "Côte d'Ivoire", dial: '+225', flag: '🇨🇮' },
]

const DEFAULT_DIAL = '+33'

/** Sépare une valeur stockée ("+33 6 12 34 56 78") en indicatif + reste local. */
export function parsePhone(value: string | null | undefined): { dial: string; local: string } {
  const v = (value || '').trim()
  if (!v) return { dial: DEFAULT_DIAL, local: '' }
  if (v.startsWith('+')) {
    // Indicatif le plus long d'abord (+352 avant +3, etc.)
    const sorted = [...COUNTRIES].sort((a, b) => b.dial.length - a.dial.length)
    const match = sorted.find(c => v.startsWith(c.dial))
    if (match) return { dial: match.dial, local: v.slice(match.dial.length).trim() }
    return { dial: DEFAULT_DIAL, local: v } // +code inconnu : conserve tel quel
  }
  return { dial: DEFAULT_DIAL, local: v }
}

function combine(dial: string, local: string): string | null {
  const lt = local.trim()
  if (!lt) return null
  // Si l'utilisateur a déjà tapé un +indicatif dans le champ, ne pas re-préfixer.
  return lt.startsWith('+') ? lt : `${dial} ${lt}`
}

interface Props {
  value: string | null | undefined
  onChange: (value: string | null) => void
  id?: string
  placeholder?: string
  disabled?: boolean
}

/**
 * Champ téléphone avec sélecteur d'indicatif (drapeau + indicatif).
 * Émet une valeur unique du type "+33 6 12 34 56 78" (ou null si vide).
 */
export default function PhoneInput({ value, onChange, id, placeholder = '6 12 34 56 78', disabled }: Props) {
  const initial = parsePhone(value)
  const [dial, setDial] = useState(initial.dial)
  const [local, setLocal] = useState(initial.local)
  const lastEmitted = useRef<string | null | undefined>(value)

  // Re-synchronise si la valeur change depuis l'extérieur (ex. chargement async en édition).
  useEffect(() => {
    if (value !== lastEmitted.current) {
      const p = parsePhone(value)
      setDial(p.dial)
      setLocal(p.local)
      lastEmitted.current = value
    }
  }, [value])

  const emit = (d: string, l: string) => {
    const combined = combine(d, l)
    lastEmitted.current = combined
    onChange(combined)
  }

  return (
    <div className="flex">
      <select
        aria-label="Indicatif pays"
        value={dial}
        disabled={disabled}
        onChange={e => { setDial(e.target.value); emit(e.target.value, local) }}
        className="px-2 py-2 rounded-l-lg border border-gray-300 border-r-0 text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
      >
        {COUNTRIES.map(c => (
          <option key={c.iso} value={c.dial}>{c.flag} {c.dial}</option>
        ))}
      </select>
      <input
        id={id}
        type="tel"
        value={local}
        disabled={disabled}
        onChange={e => { setLocal(e.target.value); emit(dial, e.target.value) }}
        placeholder={placeholder}
        className="flex-1 min-w-0 px-3 py-2 rounded-r-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
      />
    </div>
  )
}
