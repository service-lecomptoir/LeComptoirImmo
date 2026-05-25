import { useState, useEffect, useRef } from 'react'
import { Save, Eye, RotateCcw, GripVertical, CheckCircle, Loader2 } from 'lucide-react'
import { apiClient } from '@/api/client'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Spacing {
  page_margin: string
  header_mb: number
  section_mb: number
  cell_padding_v: number
  cell_padding_h: number
  line_height: number
  font_size: number
}

interface LayoutConfig {
  header_left: string[]
  header_right: string[]
  spacing: Spacing
}

const DEFAULT_CONFIG: LayoutConfig = {
  header_left: ['logo', 'sender'],
  header_right: ['recipient', 'citydate'],
  spacing: {
    page_margin: '2cm 2.5cm',
    header_mb: 14,
    section_mb: 12,
    cell_padding_v: 4,
    cell_padding_h: 10,
    line_height: 1.55,
    font_size: 10,
  },
}

// ── Définition des blocs ──────────────────────────────────────────────────────

interface Block {
  id: string
  label: string
  description: string
  color: string
  bgColor: string
}

const BLOCKS: Block[] = [
  {
    id: 'logo',
    label: 'Logo / Entête',
    description: '"LeComptoirImmo" avec bordure bleue',
    color: 'text-blue-700',
    bgColor: 'bg-blue-50 border-blue-200',
  },
  {
    id: 'sender',
    label: 'Expéditeur',
    description: 'Nom bailleur + adresse du bien',
    color: 'text-green-700',
    bgColor: 'bg-green-50 border-green-200',
  },
  {
    id: 'recipient',
    label: 'Destinataire',
    description: 'Nom locataire + adresse logement',
    color: 'text-purple-700',
    bgColor: 'bg-purple-50 border-purple-200',
  },
  {
    id: 'citydate',
    label: 'Ville + Date',
    description: '"Paris, le 26 mai 2026"',
    color: 'text-orange-700',
    bgColor: 'bg-orange-50 border-orange-200',
  },
]

function getBlock(id: string): Block {
  return BLOCKS.find((b) => b.id === id) ?? {
    id,
    label: id,
    description: '',
    color: 'text-gray-700',
    bgColor: 'bg-gray-50 border-gray-200',
  }
}

// ── Composant bloc draggable ──────────────────────────────────────────────────

interface BlockCardProps {
  blockId: string
  zone: 'left' | 'right'
  onDragStart: (e: React.DragEvent, blockId: string, fromZone: 'left' | 'right') => void
}

function BlockCard({ blockId, zone, onDragStart }: BlockCardProps) {
  const block = getBlock(blockId)
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, blockId, zone)}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-grab active:cursor-grabbing select-none ${block.bgColor}`}
    >
      <GripVertical size={14} className="text-gray-400 shrink-0" />
      <div className="min-w-0">
        <p className={`text-sm font-semibold leading-tight ${block.color}`}>{block.label}</p>
        <p className="text-xs text-gray-500 truncate">{block.description}</p>
      </div>
    </div>
  )
}

// ── Zone de dépôt ─────────────────────────────────────────────────────────────

interface DropZoneProps {
  zone: 'left' | 'right'
  blocks: string[]
  dragOver: boolean
  onDragOver: (e: React.DragEvent, zone: 'left' | 'right') => void
  onDragLeave: () => void
  onDrop: (e: React.DragEvent, zone: 'left' | 'right') => void
  onDragStart: (e: React.DragEvent, blockId: string, fromZone: 'left' | 'right') => void
}

function DropZone({ zone, blocks, dragOver, onDragOver, onDragLeave, onDrop, onDragStart }: DropZoneProps) {
  const label = zone === 'left' ? 'Colonne gauche' : 'Colonne droite'
  return (
    <div
      onDragOver={(e) => onDragOver(e, zone)}
      onDragLeave={onDragLeave}
      onDrop={(e) => onDrop(e, zone)}
      className={`flex-1 rounded-xl border-2 border-dashed p-3 min-h-[120px] transition-colors ${
        dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-gray-50'
      }`}
    >
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{label}</p>
      {blocks.length === 0 ? (
        <p className="text-xs text-gray-400 italic text-center mt-6">Déposez un bloc ici</p>
      ) : (
        <div className="space-y-2">
          {blocks.map((id) => (
            <BlockCard key={id} blockId={id} zone={zone} onDragStart={onDragStart} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Curseur de réglage ────────────────────────────────────────────────────────

interface SliderProps {
  label: string
  value: number
  min: number
  max: number
  step: number
  unit?: string
  onChange: (v: number) => void
}

function Slider({ label, value, min, max, step, unit = '', onChange }: SliderProps) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <label className="text-xs text-gray-600">{label}</label>
        <span className="text-xs font-mono text-blue-600">{value}{unit}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 accent-blue-600"
      />
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function TemplateLayoutEditor() {
  const [config, setConfig] = useState<LayoutConfig>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [previewType, setPreviewType] = useState<'avis' | 'quittance'>('avis')
  const [saved, setSaved] = useState(false)
  const [dragOverZone, setDragOverZone] = useState<'left' | 'right' | null>(null)
  const dragSrc = useRef<{ blockId: string; fromZone: 'left' | 'right' } | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await apiClient.get('/settings/template-layout')
        setConfig(data)
      } catch {
        // conserve le DEFAULT_CONFIG
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // ── Drag-and-drop ────────────────────────────────────────────────────────

  const handleDragStart = (e: React.DragEvent, blockId: string, fromZone: 'left' | 'right') => {
    dragSrc.current = { blockId, fromZone }
    e.dataTransfer.setData('text/plain', blockId)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent, zone: 'left' | 'right') => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverZone(zone)
  }

  const handleDragLeave = () => setDragOverZone(null)

  const handleDrop = (e: React.DragEvent, toZone: 'left' | 'right') => {
    e.preventDefault()
    setDragOverZone(null)
    if (!dragSrc.current) return
    const { blockId, fromZone } = dragSrc.current
    if (fromZone === toZone) return

    setConfig((prev) => {
      const from = fromZone === 'left' ? [...prev.header_left] : [...prev.header_right]
      const to = toZone === 'left' ? [...prev.header_left] : [...prev.header_right]
      const idx = from.indexOf(blockId)
      if (idx === -1) return prev
      from.splice(idx, 1)
      to.push(blockId)
      return {
        ...prev,
        header_left: toZone === 'left' ? to : from,
        header_right: toZone === 'right' ? to : from,
      }
    })
    dragSrc.current = null
  }

  // ── Espacement ───────────────────────────────────────────────────────────

  const setSpacing = (key: keyof Spacing, value: number | string) => {
    setConfig((prev) => ({ ...prev, spacing: { ...prev.spacing, [key]: value } }))
    setSaved(false)
  }

  const marginPresets: { label: string; value: string }[] = [
    { label: 'Serré', value: '1.5cm 2cm' },
    { label: 'Normal', value: '2cm 2.5cm' },
    { label: 'Aéré', value: '2.5cm 3cm' },
  ]

  // ── Sauvegarde ───────────────────────────────────────────────────────────

  const handleSave = async () => {
    setSaving(true)
    try {
      await apiClient.put('/settings/template-layout', config)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  // ── Aperçu PDF ───────────────────────────────────────────────────────────

  const handlePreview = async () => {
    setPreviewing(true)
    try {
      // Sauvegarde d'abord pour que le preview reflète les changements en cours
      await apiClient.put('/settings/template-layout', config)
      const token = localStorage.getItem('token')
      const url = `${API_BASE}/api/v1/settings/template-preview?template=${previewType}`
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      const blob = await resp.blob()
      const objUrl = URL.createObjectURL(blob)
      window.open(objUrl, '_blank')
    } catch {
      // ignore
    } finally {
      setPreviewing(false)
    }
  }

  const handleReset = () => {
    setConfig(DEFAULT_CONFIG)
    setSaved(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={24} className="animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* ── En-tête ── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mise en page des documents</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Glissez les blocs pour les repositionner. Les réglages s'appliquent aux avis d'échéance et quittances.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <RotateCcw size={14} />
            Réinitialiser
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : saved ? <CheckCircle size={14} /> : <Save size={14} />}
            {saved ? 'Enregistré !' : 'Enregistrer'}
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {/* ── En-tête de la lettre ── */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">En-tête de la lettre</h2>
          <p className="text-xs text-gray-400 mb-4">
            Glissez les blocs d'une colonne à l'autre pour changer leur position.
          </p>
          <div className="flex gap-4">
            <DropZone
              zone="left"
              blocks={config.header_left}
              dragOver={dragOverZone === 'left'}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onDragStart={handleDragStart}
            />
            <DropZone
              zone="right"
              blocks={config.header_right}
              dragOver={dragOverZone === 'right'}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onDragStart={handleDragStart}
            />
          </div>

          {/* Légende des blocs */}
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-xs text-gray-400 mb-2">Blocs disponibles :</p>
            <div className="flex flex-wrap gap-2">
              {BLOCKS.map((b) => (
                <div key={b.id} className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-xs ${b.bgColor} ${b.color}`}>
                  <span className="font-medium">{b.label}</span>
                  <span className="text-gray-400">— {b.description}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Espacement ── */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Espacement et taille de police</h2>
          <div className="grid grid-cols-2 gap-x-8 gap-y-5">
            {/* Marges */}
            <div>
              <label className="text-xs text-gray-600 block mb-2">Marges de page</label>
              <div className="flex gap-2">
                {marginPresets.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => { setSpacing('page_margin', p.value); setSaved(false) }}
                    className={`flex-1 py-1.5 text-xs rounded-lg border transition-colors ${
                      config.spacing.page_margin === p.value
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <Slider
              label="Taille de police"
              value={config.spacing.font_size}
              min={8}
              max={12}
              step={1}
              unit="pt"
              onChange={(v) => setSpacing('font_size', v)}
            />

            <Slider
              label="Interligne"
              value={config.spacing.line_height}
              min={1.3}
              max={2.0}
              step={0.05}
              onChange={(v) => setSpacing('line_height', v)}
            />

            <Slider
              label="Espace entre l'en-tête et l'objet"
              value={config.spacing.header_mb}
              min={6}
              max={30}
              step={2}
              unit="px"
              onChange={(v) => setSpacing('header_mb', v)}
            />

            <Slider
              label="Espace entre les sections"
              value={config.spacing.section_mb}
              min={6}
              max={24}
              step={2}
              unit="px"
              onChange={(v) => setSpacing('section_mb', v)}
            />

            <Slider
              label="Padding cellules (vertical)"
              value={config.spacing.cell_padding_v}
              min={2}
              max={10}
              step={1}
              unit="px"
              onChange={(v) => setSpacing('cell_padding_v', v)}
            />

            <Slider
              label="Padding cellules (horizontal)"
              value={config.spacing.cell_padding_h}
              min={4}
              max={20}
              step={2}
              unit="px"
              onChange={(v) => setSpacing('cell_padding_h', v)}
            />
          </div>
        </div>

        {/* ── Aperçu ── */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Aperçu PDF</h2>
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              <button
                onClick={() => setPreviewType('avis')}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  previewType === 'avis' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                Avis d'échéance
              </button>
              <button
                onClick={() => setPreviewType('quittance')}
                className={`px-3 py-1.5 text-sm transition-colors ${
                  previewType === 'quittance' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                Quittance
              </button>
            </div>
            <button
              onClick={handlePreview}
              disabled={previewing}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-60 transition-colors"
            >
              {previewing ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
              {previewing ? 'Génération…' : 'Ouvrir l\'aperçu PDF'}
            </button>
            <p className="text-xs text-gray-400">Utilise des données fictives • Enregistre avant de prévisualiser</p>
          </div>
        </div>
      </div>
    </div>
  )
}
