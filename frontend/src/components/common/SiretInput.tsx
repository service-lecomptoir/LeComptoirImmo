import { useEffect, useRef, useState } from 'react'
import { checkSirenSiret, cleanSiren, lookupSirenSiret, type LookupStatus } from '@/lib/siret'

interface Props {
  value: string
  /** Texte saisi (frappe libre, conservé tel quel). */
  onChange: (v: string) => void
  /**
   * Appelé quand l'établissement est retrouvé : permet de pré-remplir la raison
   * sociale. Le parent décide d'écraser ou non (en général : seulement si vide).
   */
  onResolved?: (name: string) => void
  placeholder?: string
  className?: string
  id?: string
  /** Accepter aussi un SIREN (9 chiffres) en plus du SIRET (14). Défaut : true. */
  allowSiren?: boolean
}

type State =
  | { kind: 'idle' }
  | { kind: 'invalid' }
  | { kind: 'checking' }
  | { kind: 'found'; name?: string }
  | { kind: 'not_found' }
  | { kind: 'error' }

/**
 * Champ SIREN/SIRET avec vérification : clé de Luhn (instantanée) puis contrôle
 * d'existence réelle via l'API publique « Recherche d'entreprises », avec
 * pré-remplissage de la raison sociale. NE BLOQUE JAMAIS la saisie : un numéro
 * introuvable ou une API indisponible affiche juste un avertissement.
 */
export default function SiretInput({
  value, onChange, onResolved, placeholder, className, id, allowSiren = true,
}: Props) {
  const [state, setState] = useState<State>({ kind: 'idle' })
  const lastResolved = useRef<string>('') // évite de re-remplir en boucle

  useEffect(() => {
    const d = cleanSiren(value)
    const len = d.length
    const wantedLengths = allowSiren ? [9, 14] : [14]
    if (len === 0) { setState({ kind: 'idle' }); return }
    if (!wantedLengths.includes(len)) { setState({ kind: 'idle' }); return }

    const { ok } = checkSirenSiret(d)
    if (!ok) { setState({ kind: 'invalid' }); return }

    setState({ kind: 'checking' })
    const ctrl = new AbortController()
    const t = setTimeout(async () => {
      const res: { status: LookupStatus; name?: string } = await lookupSirenSiret(d, ctrl.signal)
      if (ctrl.signal.aborted) return
      if (res.status === 'found') {
        setState({ kind: 'found', name: res.name })
        if (res.name && onResolved && lastResolved.current !== d) {
          lastResolved.current = d
          onResolved(res.name)
        }
      } else if (res.status === 'not_found') {
        setState({ kind: 'not_found' })
      } else {
        setState({ kind: 'error' })
      }
    }, 500)
    return () => { clearTimeout(t); ctrl.abort() }
    // onResolved volontairement hors deps (callback stable côté parent).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, allowSiren])

  return (
    <div>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        className={className}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
      />
      {state.kind === 'invalid' && (
        <p className="mt-1 text-xs text-amber-600">Numéro invalide (clé de contrôle incorrecte).</p>
      )}
      {state.kind === 'checking' && (
        <p className="mt-1 text-xs text-gray-400">Vérification…</p>
      )}
      {state.kind === 'found' && (
        <p className="mt-1 text-xs text-emerald-600">
          ✓ Vérifié{state.name ? ` : ${state.name}` : ''}
        </p>
      )}
      {state.kind === 'not_found' && (
        <p className="mt-1 text-xs text-amber-600">Introuvable au répertoire Sirene (vérifiez le numéro).</p>
      )}
      {/* 'error' (API indisponible) : silencieux, on n'alarme pas à tort. */}
    </div>
  )
}
