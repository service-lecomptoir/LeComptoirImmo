import { useEffect, useRef, useState } from 'react'

export interface AddressParts {
  /** Ligne de rue : n° + libellé de voie (ex. « 10 Rue de la Paix »). */
  street: string
  postcode: string
  city: string
  /** Adresse complète sur une ligne (ex. « 10 Rue de la Paix 75002 Paris »). */
  label: string
}

interface Props {
  value: string
  /** Texte saisi (frappe libre). */
  onChange: (v: string) => void
  /** Sélection d'une adresse : remplit rue + code postal + ville. */
  onSelect: (a: AddressParts) => void
  className?: string
  placeholder?: string
  id?: string
}

/**
 * Autocomplétion d'adresse (rue + code postal + ville) via la Base Adresse
 * Nationale (api-adresse.data.gouv.fr, publique, sans clé, CORS *).
 * Sélectionner une suggestion appelle `onSelect` avec les composantes séparées
 * ET met le champ courant à jour (`onChange`) avec la ligne de rue.
 * Réseau indisponible → on ignore : la saisie manuelle reste possible.
 */
export default function AddressAutocomplete({ value, onChange, onSelect, className, placeholder, id }: Props) {
  const [items, setItems] = useState<AddressParts[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const boxRef = useRef<HTMLDivElement>(null)
  const focused = useRef(false)
  const skip = useRef(false) // ne pas relancer une recherche juste après une sélection

  useEffect(() => {
    const q = (value || '').trim()
    if (skip.current) { skip.current = false; return }
    if (!focused.current) return
    if (q.length < 3) { setItems([]); setOpen(false); return }
    const ctrl = new AbortController()
    const t = setTimeout(async () => {
      try {
        const res = await fetch(
          `https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(q)}&autocomplete=1&limit=7`,
          { signal: ctrl.signal },
        )
        const data = await res.json()
        const list: AddressParts[] = (data.features || []).map((f: any) => {
          const p = f.properties || {}
          // `name` = n° + voie pour une adresse ; sinon le libellé de l'entité (rue, lieu-dit…).
          const street = p.name || ''
          return {
            street,
            postcode: p.postcode || '',
            city: p.city || '',
            label: p.label || [street, p.postcode, p.city].filter(Boolean).join(' '),
          }
        }).filter((a: AddressParts) => a.label)
        setItems(list)
        setOpen(list.length > 0)
        setActive(-1)
      } catch {
        /* réseau indisponible → saisie manuelle possible */
      }
    }, 250)
    return () => { clearTimeout(t); ctrl.abort() }
  }, [value])

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const choose = (a: AddressParts) => {
    skip.current = true
    onSelect(a)
    onChange(a.street || a.label)
    setOpen(false)
    setItems([])
  }

  return (
    <div className="relative" ref={boxRef}>
      <input
        id={id}
        type="text"
        autoComplete="off"
        className={className}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => { focused.current = true; if (items.length) setOpen(true) }}
        onBlur={() => { focused.current = false }}
        onKeyDown={e => {
          if (!open || items.length === 0) return
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a + 1, items.length - 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a - 1, 0)) }
          else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); choose(items[active]) }
          else if (e.key === 'Escape') setOpen(false)
        }}
      />
      {open && items.length > 0 && (
        <ul className="absolute z-30 mt-1 w-full max-h-56 overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg text-sm">
          {items.map((a, i) => (
            <li
              key={`${a.label}-${i}`}
              onMouseDown={e => { e.preventDefault(); choose(a) }}
              className={`px-3 py-2 cursor-pointer ${i === active ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
            >
              <span className="text-gray-900">{a.street}</span>
              {(a.postcode || a.city) && (
                <span className="text-gray-400"> : {[a.postcode, a.city].filter(Boolean).join(' ')}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
