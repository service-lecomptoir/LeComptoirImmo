import { useEffect, useRef, useState } from 'react'
import { Eraser, PenLine } from 'lucide-react'

/**
 * Pad de signature manuscrite (souris / tactile). La signature est exportée en
 * PNG sur fond blanc (data-URL) via `onChange`. « Effacer » renvoie `null`.
 * Le fond blanc évite tout artefact de transparence au rendu PDF des documents.
 */
export function SignaturePad({
  value,
  onChange,
  width = 440,
  height = 150,
}: {
  value?: string | null
  onChange: (dataUrl: string | null) => void
  width?: number
  height?: number
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const last = useRef<{ x: number; y: number } | null>(null)
  const [hasInk, setHasInk] = useState(false)

  // Initialise le fond blanc puis, le cas échéant, redessine la signature existante.
  useEffect(() => {
    const cv = canvasRef.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, cv.width, cv.height)
    ctx.lineWidth = 2.2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.strokeStyle = '#1f2937'
    if (value) {
      const img = new Image()
      img.onload = () => { ctx.drawImage(img, 0, 0, cv.width, cv.height); setHasInk(true) }
      img.src = value
    }
    // Volontairement sans dépendances : initialisation au montage uniquement.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const pos = (e: React.PointerEvent) => {
    const cv = canvasRef.current!
    const r = cv.getBoundingClientRect()
    return { x: (e.clientX - r.left) * (cv.width / r.width), y: (e.clientY - r.top) * (cv.height / r.height) }
  }

  const start = (e: React.PointerEvent) => {
    e.preventDefault()
    drawing.current = true
    last.current = pos(e)
    canvasRef.current?.setPointerCapture(e.pointerId)
  }

  const move = (e: React.PointerEvent) => {
    if (!drawing.current) return
    const ctx = canvasRef.current?.getContext('2d')
    if (!ctx || !last.current) return
    const p = pos(e)
    ctx.beginPath()
    ctx.moveTo(last.current.x, last.current.y)
    ctx.lineTo(p.x, p.y)
    ctx.stroke()
    last.current = p
    if (!hasInk) setHasInk(true)
  }

  const end = () => {
    if (!drawing.current) return
    drawing.current = false
    last.current = null
    const cv = canvasRef.current
    if (cv && hasInk) onChange(cv.toDataURL('image/png'))
  }

  const clear = () => {
    const cv = canvasRef.current
    const ctx = cv?.getContext('2d')
    if (!cv || !ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, cv.width, cv.height)
    setHasInk(false)
    onChange(null)
  }

  return (
    <div>
      <div className="inline-block rounded-lg border border-gray-300 bg-white overflow-hidden">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onPointerDown={start}
          onPointerMove={move}
          onPointerUp={end}
          onPointerLeave={end}
          className="touch-none cursor-crosshair block"
          style={{ width: '100%', maxWidth: width, height }}
        />
      </div>
      <div className="flex items-center gap-3 mt-2">
        <button type="button" onClick={clear}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
          <Eraser size={14} /> Effacer
        </button>
        <span className="text-xs text-gray-400 inline-flex items-center gap-1">
          <PenLine size={12} /> Signez dans le cadre, puis enregistrez.
        </span>
      </div>
    </div>
  )
}
