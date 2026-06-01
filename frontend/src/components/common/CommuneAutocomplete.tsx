import { useEffect, useRef, useState } from 'react'

interface Commune {
  zip: string
  city: string
}

interface Props {
  value: string
  /** Texte saisi (frappe libre). */
  onChange: (v: string) => void
  /** Sélection d'une commune : remplit code postal + ville. */
  onSelect: (c: Commune) => void
  /** Champ piloté : 'city' affiche la ville, 'postcode' affiche le code postal. */
  display: 'city' | 'postcode'
  className?: string
  placeholder?: string
  id?: string
}

/**
 * Autocomplétion code postal / ville via la Base Adresse Nationale
 * (api-adresse.data.gouv.fr, public, CORS *). La recherche accepte un nom de
 * commune OU un code postal ; sélectionner remplit les deux champs.
 */
export default function CommuneAutocomplete({ value, onChange, onSelect, display, className, placeholder, id }: Props) {
  const [items, setItems] = useState<Commune[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const boxRef = useRef<HTMLDivElement>(null)
  const focused = useRef(false)
  const skip = useRef(false) // ne pas relancer une recherche juste après une sélection

  useEffect(() => {
    const q = (value || '').trim()
    if (skip.current) { skip.current = false; return }
    if (!focused.current) return            // évite de déclencher l'autre champ (rempli par programme)
    if (q.length < 2) { setItems([]); setOpen(false); return }
    const ctrl = new AbortController()
    const t = setTimeout(async () => {
      try {
        const res = await fetch(
          `https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(q)}&type=municipality&autocomplete=1&limit=7`,
          { signal: ctrl.signal },
        )
        const data = await res.json()
        const list: Commune[] = (data.features || []).map((f: any) => ({
          zip: f.properties?.postcode || '',
          city: f.properties?.city || f.properties?.name || '',
        })).filter((c: Commune) => c.city)
        setItems(list)
        setOpen(list.length > 0)
        setActive(-1)
      } catch {
        /* réseau indisponible → on ignore, saisie manuelle possible */
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

  const choose = (c: Commune) => {
    skip.current = true
    onSelect(c)
    onChange(display === 'city' ? c.city : c.zip)
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
          {items.map((c, i) => (
            <li
              key={`${c.zip}-${c.city}-${i}`}
              onMouseDown={e => { e.preventDefault(); choose(c) }}
              className={`px-3 py-2 cursor-pointer flex items-center justify-between gap-2 ${i === active ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
            >
              <span className="font-medium text-gray-900">{c.city}</span>
              <span className="text-gray-400">{c.zip}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
