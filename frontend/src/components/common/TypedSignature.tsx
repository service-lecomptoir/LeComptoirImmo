import { useEffect, useRef, useState } from 'react'
import { Eraser, Type, PenTool } from 'lucide-react'

/** Polices manuscrites proposées (chargées via Google Fonts dans index.html). */
const FONTS = [
  { id: 'Dancing Script', label: 'Manuscrite' },
  { id: 'Great Vibes', label: 'Élégante' },
  { id: 'Sacramento', label: 'Fine' },
  { id: 'Allura', label: 'Raffinée' },
  { id: 'Pacifico', label: 'Ronde' },
  { id: 'Caveat', label: 'Décontractée' },
]

export type SignatureMode = 'type' | 'draw'
export interface SignatureValue {
  dataUrl: string | null   // PNG (data-URL) ou null si vidée
  mode: SignatureMode
  text: string             // texte saisi (mode frappe), '' en mode dessin
  font: string             // police choisie (mode frappe)
}

/**
 * Signature numérique, deux modes au choix :
 *  - « Frappe » : l'utilisateur tape son nom et choisit un style d'écriture ;
 *  - « Dessin » : tracé libre à la souris / au doigt.
 * Le rendu est exporté en PNG (data-URL) via `onChange`, accompagné du mode,
 * du texte et de la police pour permettre la réédition (la case texte reflète
 * la signature enregistrée).
 */
export function TypedSignature({
  value,
  initialMode,
  initialText,
  initialFont,
  onChange,
  defaultText = '',
  width = 460,
  height = 150,
}: {
  value?: string | null
  initialMode?: SignatureMode | null
  initialText?: string | null
  initialFont?: string | null
  onChange: (sig: SignatureValue) => void
  defaultText?: string
  width?: number
  height?: number
}) {
  const [mode, setMode] = useState<SignatureMode>(initialMode || 'type')
  // En mode frappe : on restaure UNIQUEMENT le texte enregistré. Le `defaultText`
  // (nom du bailleur) n'est qu'une SUGGESTION cliquable, jamais une valeur
  // pré-remplie : sinon une signature supprimée semble toujours contenir ce nom.
  const [text, setText] = useState(initialText || '')
  const [font, setFont] = useState(initialFont || FONTS[0].id)
  // `edited` passe à true dès que l'utilisateur modifie quoi que ce soit. Tant
  // qu'il est false et qu'une signature existe, on l'affiche telle quelle.
  const [edited, setEdited] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const lastPt = useRef<{ x: number; y: number } | null>(null)

  const emit = (dataUrl: string | null, m: SignatureMode, t: string, f: string) =>
    onChange({ dataUrl, mode: m, text: t, font: f })

  const drawImageOnto = (ctx: CanvasRenderingContext2D, src: string) =>
    new Promise<void>(resolve => {
      const img = new Image()
      img.onload = () => { ctx.drawImage(img, 0, 0, ctx.canvas.width, ctx.canvas.height); resolve() }
      img.onerror = () => resolve()
      img.src = src
    })

  const drawText = async (ctx: CanvasRenderingContext2D, t: string, f: string) => {
    if (!t) return
    try { await (document as any).fonts?.load(`72px '${f}'`) } catch { /* repli police système */ }
    ctx.fillStyle = '#1f2937'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    let size = 76
    ctx.font = `${size}px '${f}', cursive`
    const maxW = ctx.canvas.width - 28
    while (size > 20 && ctx.measureText(t).width > maxW) {
      size -= 2
      ctx.font = `${size}px '${f}', cursive`
    }
    ctx.fillText(t, ctx.canvas.width / 2, ctx.canvas.height / 2 + 4)
  }

  // ── Mode FRAPPE : (re)trace le texte à chaque changement, émet si modifié.
  useEffect(() => {
    if (mode !== 'type') return
    let cancelled = false
    ;(async () => {
      const cv = canvasRef.current
      if (!cv) return
      const ctx = cv.getContext('2d')
      if (!ctx) return
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, cv.width, cv.height)
      // Tant que l'utilisateur n'a rien modifié : afficher la signature enregistrée
      // si elle existe, sinon laisser le cadre VIDE (pas d'aperçu du nom par défaut,
      // sinon une signature supprimée semble toujours présente). Aucune émission.
      if (!edited) {
        if (value) await drawImageOnto(ctx, value)
        return
      }
      const t = text.trim()
      if (t) {
        await drawText(ctx, t, font)
      }
      if (cancelled) return
      emit(t ? cv.toDataURL('image/png') : null, 'type', t, font)
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, font, mode, edited, value])

  // ── Mode DESSIN : affiche la signature enregistrée au montage (avant édition).
  useEffect(() => {
    if (mode !== 'draw' || edited) return
    const cv = canvasRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, cv.width, cv.height)
    if (value) drawImageOnto(ctx, value)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  const switchMode = (m: SignatureMode) => {
    if (m === mode) return
    const cv = canvasRef.current
    const ctx = cv?.getContext('2d')
    if (ctx && cv) { ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cv.width, cv.height) }
    setEdited(false)
    setMode(m)
  }

  // ── Tracé libre (mode dessin) ───────────────────────────────────────────────
  const ptFromEvent = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const cv = canvasRef.current!
    const rect = cv.getBoundingClientRect()
    return {
      x: (e.clientX - rect.left) * (cv.width / rect.width),
      y: (e.clientY - rect.top) * (cv.height / rect.height),
    }
  }
  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (mode !== 'draw') return
    const cv = canvasRef.current!
    const ctx = cv.getContext('2d')!
    // Premier tracé après une signature existante : repart d'une zone blanche.
    if (!edited) { ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cv.width, cv.height) }
    setEdited(true)
    drawing.current = true
    lastPt.current = ptFromEvent(e)
    cv.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (mode !== 'draw' || !drawing.current) return
    const cv = canvasRef.current!
    const ctx = cv.getContext('2d')!
    const p = ptFromEvent(e)
    ctx.strokeStyle = '#1f2937'
    ctx.lineWidth = 2.5
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.beginPath()
    ctx.moveTo(lastPt.current!.x, lastPt.current!.y)
    ctx.lineTo(p.x, p.y)
    ctx.stroke()
    lastPt.current = p
  }
  const endStroke = () => {
    if (mode !== 'draw' || !drawing.current) return
    drawing.current = false
    const cv = canvasRef.current!
    emit(cv.toDataURL('image/png'), 'draw', '', font)
  }

  const clear = () => {
    setEdited(true)
    const cv = canvasRef.current
    const ctx = cv?.getContext('2d')
    if (ctx && cv) { ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cv.width, cv.height) }
    if (mode === 'type') setText('')
    else emit(null, 'draw', '', font)
  }

  const tabCls = (active: boolean) =>
    `inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium ${
      active ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 text-gray-600 hover:border-gray-300'
    }`

  return (
    <div>
      {/* Choix du mode */}
      <div className="flex gap-2 mb-3">
        <button type="button" onClick={() => switchMode('type')} className={tabCls(mode === 'type')}>
          <Type size={15} /> Frappe
        </button>
        <button type="button" onClick={() => switchMode('draw')} className={tabCls(mode === 'draw')}>
          <PenTool size={15} /> Dessin
        </button>
      </div>

      {mode === 'type' && (
        <>
          <input
            value={text}
            onChange={e => { setEdited(true); setText(e.target.value) }}
            placeholder="Tapez votre nom"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-2"
          />
          {defaultText && !text.trim() && (
            <button type="button" onClick={() => { setEdited(true); setText(defaultText) }}
              className="text-xs text-blue-600 hover:underline mb-2">
              Utiliser « {defaultText} »
            </button>
          )}
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
        </>
      )}

      <div className="inline-block rounded-lg border border-gray-300 bg-white overflow-hidden">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endStroke}
          onPointerLeave={endStroke}
          style={{ width: '100%', maxWidth: width, height, touchAction: 'none', cursor: mode === 'draw' ? 'crosshair' : 'default' }}
        />
      </div>
      <div className="flex items-center gap-3 mt-2">
        <button type="button" onClick={clear}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
          <Eraser size={14} /> Effacer
        </button>
        <span className="text-xs text-gray-400">
          {mode === 'draw'
            ? 'Dessinez votre signature dans le cadre avec la souris, puis enregistrez.'
            : (value && !edited
                ? 'Une signature est déjà enregistrée. Tapez votre nom pour la remplacer.'
                : 'Tapez votre nom, choisissez un style, puis enregistrez.')}
        </span>
      </div>
    </div>
  )
}
