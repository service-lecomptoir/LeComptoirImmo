import { useEffect, useRef, useState } from 'react'
import { Eraser } from 'lucide-react'

/** Polices manuscrites proposées (chargées via Google Fonts dans index.html). */
const FONTS = [
  { id: 'Dancing Script', label: 'Manuscrite' },
  { id: 'Great Vibes', label: 'Élégante' },
  { id: 'Sacramento', label: 'Fine' },
  { id: 'Allura', label: 'Raffinée' },
  { id: 'Pacifico', label: 'Ronde' },
  { id: 'Caveat', label: 'Décontractée' },
]

/**
 * Signature tapée au clavier : l'utilisateur saisit son nom et choisit un style
 * d'écriture. Le rendu est tracé sur un canvas (fond blanc) puis exporté en PNG
 * (data-URL) via `onChange` — même format que l'ancienne signature, donc aucun
 * changement côté stockage ni génération PDF.
 */
export function TypedSignature({
  value,
  onChange,
  defaultText = '',
  width = 460,
  height = 150,
}: {
  value?: string | null
  onChange: (dataUrl: string | null) => void
  defaultText?: string
  width?: number
  height?: number
}) {
  const [text, setText] = useState(defaultText)
  const [font, setFont] = useState(FONTS[0].id)
  // `edited` passe à true dès que l'utilisateur saisit, change de style ou efface.
  // Tant qu'il est false et qu'une signature existe déjà, on l'affiche telle quelle
  // (PNG enregistré) sans la réémettre, pour ne pas la perdre ni la remplacer.
  const [edited, setEdited] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const cv = canvasRef.current
      if (!cv) return
      const ctx = cv.getContext('2d')
      if (!ctx) return
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, cv.width, cv.height)

      // Avant toute modification : afficher la signature déjà enregistrée telle
      // quelle (sans émettre), au lieu de prévisualiser le nom par défaut.
      if (!edited && value) {
        await new Promise<void>(resolve => {
          const img = new Image()
          img.onload = () => { if (!cancelled) ctx.drawImage(img, 0, 0, cv.width, cv.height); resolve() }
          img.onerror = () => resolve()
          img.src = value
        })
        return
      }

      const t = text.trim()
      if (t) {
        try { await (document as any).fonts?.load(`72px '${font}'`) } catch { /* repli police système */ }
        if (cancelled) return
        ctx.fillStyle = '#1f2937'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        let size = 76
        ctx.font = `${size}px '${font}', cursive`
        const maxW = cv.width - 28
        while (size > 20 && ctx.measureText(t).width > maxW) {
          size -= 2
          ctx.font = `${size}px '${font}', cursive`
        }
        ctx.fillText(t, cv.width / 2, cv.height / 2 + 4)
      }
      // Pas d'émission tant que l'utilisateur n'a rien modifié (préserve l'existant).
      if (!edited) return
      onChange(t ? cv.toDataURL('image/png') : null)
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, font, edited, value])

  const clear = () => { setEdited(true); setText('') }

  return (
    <div>
      <input
        value={text}
        onChange={e => { setEdited(true); setText(e.target.value) }}
        placeholder="Tapez votre nom"
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
      />
      <div className="flex flex-wrap gap-1.5 mb-2">
        {FONTS.map(f => (
          <button
            key={f.id}
            type="button"
            onClick={() => { setEdited(true); setFont(f.id) }}
            title={f.label}
            className={`px-3 py-1.5 rounded-lg border text-lg leading-none ${font === f.id ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
            style={{ fontFamily: `'${f.id}', cursive` }}
          >
            {(text.trim().split(/\s+/)[0] || 'Signature')}
          </button>
        ))}
      </div>
      <div className="inline-block rounded-lg border border-gray-300 bg-white overflow-hidden">
        <canvas ref={canvasRef} width={width} height={height} style={{ width: '100%', maxWidth: width, height }} />
      </div>
      <div className="flex items-center gap-3 mt-2">
        <button type="button" onClick={clear}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
          <Eraser size={14} /> Effacer
        </button>
        <span className="text-xs text-gray-400">
          {value && !edited ? 'Une signature est déjà enregistrée. Tapez votre nom pour la remplacer.' : 'Choisissez un style, puis enregistrez.'}
        </span>
      </div>
    </div>
  )
}
