import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ArrowLeft, Save, X, Star, Check, RefreshCw, Download,
  Plus, Trash2, Pencil, Image as ImageIcon, FileText, GripHorizontal,
} from 'lucide-react'
import { apiClient } from '@/api/client'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ── Constantes ────────────────────────────────────────────────────────────────

const TEMPLATE_TYPES = [
  { value: 'avis_echeance',      label: "Avis d'échéance" },
  { value: 'quittance',          label: 'Quittance de loyer' },
  { value: 'lettre_relance',     label: 'Lettre de relance' },
  { value: 'lettre_resiliation', label: 'Lettre de résiliation' },
  { value: 'contrat_bail',       label: 'Contrat de bail' },
  { value: 'etat_des_lieux',     label: 'État des lieux' },
]

const PRESET_COLORS = ['#1E3A5F', '#2563EB', '#059669', '#D97706', '#7C3AED', '#DC2626', '#374151']

// Variables organisées par catégorie
const VAR_CATEGORIES = [
  {
    label: 'Locataire', color: '#2563EB', bg: '#dbeafe', text: '#1d4ed8',
    vars: [
      { key: '{{tenant_name}}', label: 'Nom locataire' },
    ],
  },
  {
    label: 'Bien', color: '#059669', bg: '#d1fae5', text: '#047857',
    vars: [
      { key: '{{property_name}}', label: 'Propriété' },
      { key: '{{unit_ref}}', label: 'Logement' },
      { key: '{{property_address}}', label: 'Adresse' },
    ],
  },
  {
    label: 'Loyer', color: '#D97706', bg: '#fef3c7', text: '#92400e',
    vars: [
      { key: '{{rent_amount}}', label: 'Loyer' },
      { key: '{{charges_amount}}', label: 'Charges' },
      { key: '{{total_due}}', label: 'Total dû' },
      { key: '{{amount_paid}}', label: 'Montant payé' },
      { key: '{{apl_amount}}', label: 'APL' },
    ],
  },
  {
    label: 'Dates', color: '#7C3AED', bg: '#ede9fe', text: '#5b21b6',
    vars: [
      { key: '{{due_date}}', label: 'Échéance' },
      { key: '{{month}}', label: 'Mois' },
      { key: '{{date}}', label: "Date du jour" },
    ],
  },
  {
    label: 'Cabinet', color: '#374151', bg: '#f3f4f6', text: '#111827',
    vars: [
      { key: '{{company_name}}', label: 'Cabinet' },
    ],
  },
]

// Map clé → couleurs pour le preview
const VAR_COLOR_MAP: Record<string, { bg: string; text: string }> = {}
VAR_CATEGORIES.forEach(cat => {
  cat.vars.forEach(v => { VAR_COLOR_MAP[v.key] = { bg: cat.bg, text: cat.text } })
})

const typeLabel = (val: string) => TEMPLATE_TYPES.find(t => t.value === val)?.label ?? val

// ── Types ─────────────────────────────────────────────────────────────────────

interface Template {
  id: string
  name: string
  template_type: string
  header_color?: string
  company_name?: string
  company_address?: string
  company_phone?: string
  company_email?: string
  company_siret?: string
  content_html?: string
  footer_text?: string
  logo_url?: string | null
  is_default: boolean
  is_active: boolean
}

interface FormData {
  name: string
  template_type: string
  header_color: string
  company_name: string
  company_address: string
  company_phone: string
  company_email: string
  company_siret: string
  content_html: string
  footer_text: string
  is_default: boolean
}

const EMPTY_FORM: FormData = {
  name: '', template_type: 'avis_echeance', header_color: '#1E3A5F',
  company_name: '', company_address: '', company_phone: '',
  company_email: '', company_siret: '', content_html: '', footer_text: '', is_default: false,
}

// ── Helpers preview ───────────────────────────────────────────────────────────

function renderPreviewHtml(html: string): string {
  if (!html) return '<p style="color:#9ca3af;font-style:italic;margin:0">Le contenu du document apparaîtra ici…</p>'
  return html.replace(/\{\{\w+\}\}/g, (match) => {
    const c = VAR_COLOR_MAP[match] ?? { bg: '#f3f4f6', text: '#374151' }
    return `<span style="background:${c.bg};color:${c.text};padding:1px 5px;border-radius:3px;font-size:0.78em;font-weight:700;white-space:nowrap;font-family:monospace;">${match}</span>`
  })
}

// ── Composant éditeur principal ───────────────────────────────────────────────

interface EditorProps {
  template: Template | null
  onBack: () => void
  onSaved: () => void
}

function TemplateEditorPanel({ template, onBack, onSaved }: EditorProps) {
  const [form, setForm] = useState<FormData>(
    template ? {
      name: template.name,
      template_type: template.template_type,
      header_color: template.header_color ?? '#1E3A5F',
      company_name: template.company_name ?? '',
      company_address: template.company_address ?? '',
      company_phone: template.company_phone ?? '',
      company_email: template.company_email ?? '',
      company_siret: template.company_siret ?? '',
      content_html: template.content_html ?? '',
      footer_text: template.footer_text ?? '',
      is_default: template.is_default,
    } : { ...EMPTY_FORM }
  )

  const [logoPreview, setLogoPreview] = useState<string | null>(
    template?.logo_url ? `${API_BASE}${template.logo_url}` : null
  )
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [dragOverTextarea, setDragOverTextarea] = useState(false)

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const cursorPosRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const set = (field: keyof FormData, value: string | boolean) =>
    setForm(f => ({ ...f, [field]: value }))

  // ── Logo ────────────────────────────────────────────────────────────────────

  const handleLogoChange = (file: File) => {
    setLogoFile(file)
    const reader = new FileReader()
    reader.onload = e => setLogoPreview(e.target?.result as string)
    reader.readAsDataURL(file)
  }

  const handleLogoDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) handleLogoChange(file)
  }

  // ── Variable drag & drop vers textarea ──────────────────────────────────────

  const insertVar = useCallback((varKey: string, pos?: number) => {
    const ta = textareaRef.current
    if (!ta) {
      set('content_html', (form.content_html ?? '') + varKey)
      return
    }
    const insertAt = pos ?? cursorPosRef.current
    const cur = form.content_html ?? ''
    const next = cur.slice(0, insertAt) + varKey + cur.slice(insertAt)
    set('content_html', next)
    setTimeout(() => {
      ta.focus()
      ta.setSelectionRange(insertAt + varKey.length, insertAt + varKey.length)
    }, 0)
  }, [form.content_html])

  const handleTextareaClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    cursorPosRef.current = e.currentTarget.selectionStart
  }
  const handleTextareaKeyUp = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    cursorPosRef.current = e.currentTarget.selectionStart
  }

  const handleVarDragStart = (e: React.DragEvent, varKey: string) => {
    e.dataTransfer.setData('text/plain', varKey)
    e.dataTransfer.effectAllowed = 'copy'
  }

  const handleTextareaDragOver = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
    setDragOverTextarea(true)
  }

  const handleTextareaDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault()
    setDragOverTextarea(false)
    const varKey = e.dataTransfer.getData('text/plain')
    if (!varKey) return
    const ta = e.currentTarget
    // Obtenir la position d'insertion
    const pos = (ta as any).selectionStart ?? form.content_html.length
    insertVar(varKey, pos)
  }

  // ── Sauvegarde ───────────────────────────────────────────────────────────────

  const handleSave = async () => {
    if (!form.name.trim()) { setError('Le nom est obligatoire'); return }
    setSaving(true); setError('')
    try {
      let savedId = template?.id
      if (template?.id) {
        await apiClient.patch(`/templates/${template.id}`, form)
      } else {
        const r = await apiClient.post<Template>('/templates', form)
        savedId = r.data.id
      }
      // Upload logo si nouveau fichier
      if (logoFile && savedId) {
        const fd = new FormData()
        fd.append('file', logoFile)
        await apiClient.post(`/templates/${savedId}/upload-logo`, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
      onSaved()
      onBack()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const inp = 'w-full border border-gray-200 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50 focus:bg-white'

  // ── Rendu ─────────────────────────────────────────────────────────────────

  return (
    <div className="h-full flex flex-col bg-white">

      {/* ── Barre supérieure ───────────────────────────────────────────────── */}
      <div className="h-14 px-4 border-b flex items-center gap-3 shrink-0 bg-white z-10 shadow-sm">
        <button onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors shrink-0">
          <ArrowLeft size={16} />
          <span className="hidden sm:inline">Retour</span>
        </button>

        <div className="h-5 w-px bg-gray-200 shrink-0" />

        <input
          value={form.name}
          onChange={e => set('name', e.target.value)}
          placeholder="Nom du template…"
          className="flex-1 min-w-0 text-sm font-semibold text-gray-800 bg-transparent border-b-2 border-transparent focus:border-blue-500 outline-none px-1 py-0.5 placeholder-gray-400"
        />

        <select value={form.template_type} onChange={e => set('template_type', e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-700 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 shrink-0">
          {TEMPLATE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>

        {/* Couleur header */}
        <div className="flex items-center gap-1 shrink-0">
          {PRESET_COLORS.map(c => (
            <button key={c} type="button" onClick={() => set('header_color', c)}
              className={`w-5 h-5 rounded-full border-2 transition-transform hover:scale-110 ${form.header_color === c ? 'border-gray-700 scale-110' : 'border-white shadow-sm'}`}
              style={{ backgroundColor: c }} title={c} />
          ))}
          <input type="color" value={form.header_color}
            onChange={e => set('header_color', e.target.value)}
            className="w-5 h-5 rounded cursor-pointer border border-gray-200"
            title="Couleur personnalisée" />
        </div>

        <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer shrink-0">
          <input type="checkbox" checked={form.is_default}
            onChange={e => set('is_default', e.target.checked)} className="rounded" />
          <Star size={12} className={form.is_default ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'} />
          <span className="hidden md:inline">Par défaut</span>
        </label>

        {error && (
          <span className="text-xs text-red-600 truncate max-w-48">{error}</span>
        )}

        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 shrink-0 transition-colors">
          {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
          <span>Enregistrer</span>
        </button>
      </div>

      {/* ── Corps principal ────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* ── Colonne gauche : paramètres ─────────────────────────────────── */}
        <div className="w-72 shrink-0 border-r overflow-y-auto bg-gray-50">
          <div className="p-4 space-y-5">

            {/* Logo */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Logo</p>
              <div
                onDragOver={e => e.preventDefault()}
                onDrop={handleLogoDrop}
                className={`relative border-2 border-dashed rounded-xl transition-colors cursor-pointer ${
                  logoPreview ? 'border-gray-200 bg-white' : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50'
                }`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input ref={fileInputRef} type="file" accept="image/*" className="hidden"
                  onChange={e => { if (e.target.files?.[0]) handleLogoChange(e.target.files[0]) }} />

                {logoPreview ? (
                  <div className="relative p-3 flex items-center justify-center">
                    <img src={logoPreview} alt="Logo" className="max-h-16 max-w-full object-contain" />
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); setLogoPreview(null); setLogoFile(null) }}
                      className="absolute top-1 right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600">
                      <X size={10} />
                    </button>
                  </div>
                ) : (
                  <div className="py-5 flex flex-col items-center gap-2 text-gray-400">
                    <ImageIcon size={24} />
                    <p className="text-xs text-center">Glissez un logo<br />ou cliquez pour choisir</p>
                    <p className="text-xs text-gray-300">PNG, JPG, SVG, WebP</p>
                  </div>
                )}
              </div>
            </div>

            {/* Informations cabinet */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Votre cabinet</p>
              <div className="space-y-2">
                <input className={inp} value={form.company_name}
                  onChange={e => set('company_name', e.target.value)} placeholder="Nom de la société" />
                <input className={inp} value={form.company_address}
                  onChange={e => set('company_address', e.target.value)} placeholder="Adresse" />
                <div className="grid grid-cols-2 gap-2">
                  <input className={inp} value={form.company_phone}
                    onChange={e => set('company_phone', e.target.value)} placeholder="Téléphone" />
                  <input className={inp} value={form.company_email}
                    onChange={e => set('company_email', e.target.value)} placeholder="Email" />
                </div>
                <input className={inp} value={form.company_siret}
                  onChange={e => set('company_siret', e.target.value)} placeholder="SIRET" />
              </div>
            </div>

            {/* Pied de page */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Pied de page</p>
              <textarea
                rows={2}
                className={`${inp} resize-none`}
                value={form.footer_text}
                onChange={e => set('footer_text', e.target.value)}
                placeholder="Mentions légales, informations complémentaires…"
              />
            </div>

          </div>
        </div>

        {/* ── Colonne centrale : variables + éditeur ──────────────────────── */}
        <div className="flex-1 min-w-0 flex flex-col border-r">

          {/* Variables draggables */}
          <div className="shrink-0 px-3 py-2 border-b bg-white">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-400 font-medium shrink-0 flex items-center gap-1">
                <GripHorizontal size={12} />
                Glissez
              </span>
              {VAR_CATEGORIES.map(cat => (
                <div key={cat.label} className="flex items-center gap-1">
                  {cat.vars.map(v => (
                    <div
                      key={v.key}
                      draggable
                      onDragStart={e => handleVarDragStart(e, v.key)}
                      onClick={() => insertVar(v.key)}
                      className="flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold cursor-grab active:cursor-grabbing select-none border transition-all hover:scale-105 hover:shadow-sm"
                      style={{
                        backgroundColor: cat.bg,
                        color: cat.text,
                        borderColor: cat.bg,
                      }}
                      title={`Glisser ou cliquer pour insérer ${v.key}`}
                    >
                      <GripHorizontal size={10} className="opacity-60" />
                      {v.label}
                    </div>
                  ))}
                  {cat !== VAR_CATEGORIES[VAR_CATEGORIES.length - 1] && (
                    <div className="w-px h-4 bg-gray-200 mx-1" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Zone d'édition de contenu */}
          <div className="flex-1 flex flex-col p-3 gap-2 min-h-0">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Contenu du document
              </p>
              <span className="text-xs text-gray-400">Glissez les marqueurs ci-dessus dans le texte</span>
            </div>

            <div className={`relative flex-1 min-h-0 rounded-xl border-2 transition-colors ${
              dragOverTextarea ? 'border-blue-400 bg-blue-50' : 'border-gray-200'
            }`}>
              {dragOverTextarea && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                  <div className="bg-blue-500 text-white px-4 py-2 rounded-full text-sm font-semibold shadow-lg">
                    Déposer ici
                  </div>
                </div>
              )}
              <textarea
                ref={textareaRef}
                id="tpl-content"
                className="w-full h-full px-3 py-3 text-sm font-mono resize-none focus:outline-none bg-transparent rounded-xl"
                placeholder="Rédigez le contenu du document ici…
&#10;Exemple :
&#10;Cher(e) {{tenant_name}},
&#10;Votre loyer du mois de {{month}} d'un montant de {{total_due}} € est à régler avant le {{due_date}}.
&#10;
&#10;Cordialement,
&#10;{{company_name}}"
                value={form.content_html}
                onChange={e => {
                  set('content_html', e.target.value)
                  cursorPosRef.current = e.target.selectionStart
                }}
                onClick={handleTextareaClick}
                onKeyUp={handleTextareaKeyUp}
                onDragOver={handleTextareaDragOver}
                onDragLeave={() => setDragOverTextarea(false)}
                onDrop={handleTextareaDrop}
              />
            </div>
          </div>
        </div>

        {/* ── Colonne droite : aperçu A4 ──────────────────────────────────── */}
        <div className="w-[380px] shrink-0 bg-gray-100 flex flex-col items-center overflow-y-auto py-4 px-3 gap-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider self-start">
            Aperçu document
          </p>

          {/* Document A4 simulé à scale 0.47 */}
          <div style={{ width: 373 }} className="flex-shrink-0">
            <div
              style={{
                width: 794,
                minHeight: 1123,
                transform: 'scale(0.47)',
                transformOrigin: 'top left',
                backgroundColor: '#fff',
                boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
                borderRadius: 4,
                fontFamily: 'Georgia, "Times New Roman", serif',
                position: 'relative',
              }}
            >
              {/* En-tête coloré */}
              <div style={{
                backgroundColor: form.header_color,
                padding: '28px 48px',
                display: 'flex',
                alignItems: 'center',
                gap: 24,
                minHeight: 100,
              }}>
                {logoPreview && (
                  <img src={logoPreview} alt="Logo"
                    style={{ height: 56, width: 'auto', maxWidth: 120, objectFit: 'contain', flexShrink: 0 }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ color: '#fff', fontSize: 20, fontWeight: 700, fontFamily: 'Arial, sans-serif' }}>
                    {form.company_name || <span style={{ opacity: 0.5 }}>Nom de votre cabinet</span>}
                  </div>
                  {form.company_address && (
                    <div style={{ color: 'rgba(255,255,255,0.8)', fontSize: 12, marginTop: 4, fontFamily: 'Arial, sans-serif' }}>
                      {form.company_address}
                    </div>
                  )}
                  {(form.company_phone || form.company_email) && (
                    <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11, marginTop: 3, fontFamily: 'Arial, sans-serif' }}>
                      {[form.company_phone, form.company_email].filter(Boolean).join(' · ')}
                    </div>
                  )}
                </div>
                {form.company_siret && (
                  <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: 10, textAlign: 'right', fontFamily: 'Arial, sans-serif' }}>
                    SIRET<br />{form.company_siret}
                  </div>
                )}
              </div>

              {/* Corps du document */}
              <div style={{ padding: '40px 48px', minHeight: 900 }}>
                <div
                  style={{ fontSize: 14, lineHeight: '1.8', color: '#1f2937', fontFamily: 'Arial, sans-serif' }}
                  dangerouslySetInnerHTML={{ __html: renderPreviewHtml(form.content_html) }}
                />
              </div>

              {/* Pied de page */}
              <div style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                borderTop: '1px solid #e5e7eb',
                padding: '16px 48px',
                backgroundColor: '#f9fafb',
              }}>
                <div style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'Arial, sans-serif' }}>
                  {form.footer_text || <span style={{ fontStyle: 'italic' }}>Pied de page…</span>}
                </div>
              </div>
            </div>
          </div>

          {/* Indicateur hauteur page */}
          <p className="text-xs text-gray-400 text-center mt-1">
            Aperçu réel du document PDF généré
          </p>
        </div>

      </div>
    </div>
  )
}

// ── Page liste des templates ──────────────────────────────────────────────────

export default function TemplateEditor() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [editTemplate, setEditTemplate] = useState<Template | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [initLoading, setInitLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const params = filterType ? { template_type: filterType } : {}
      const r = await apiClient.get<Template[]>('/templates', { params })
      setTemplates(r.data)
    } catch {
      setTemplates([])
    } finally {
      setLoading(false)
    }
  }

  const initDefaults = async () => {
    setInitLoading(true)
    try {
      const r = await apiClient.post<{ created: number; message: string }>('/templates/initialize-defaults')
      await load()
      setSuccessMsg(r.data.message)
      setTimeout(() => setSuccessMsg(''), 3000)
    } finally {
      setInitLoading(false)
    }
  }

  const deleteTemplate = async (t: Template) => {
    if (!confirm(`Supprimer "${t.name}" ?`)) return
    try {
      await apiClient.delete(`/templates/${t.id}`)
      await load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la suppression')
    }
  }

  const openNew = () => { setEditTemplate(null); setEditMode(true) }
  const openEdit = (t: Template) => { setEditTemplate(t); setEditMode(true) }
  const handleBack = () => { setEditMode(false); setEditTemplate(null) }
  const onSaved = () => { load(); setSuccessMsg('Template enregistré'); setTimeout(() => setSuccessMsg(''), 3000) }

  useEffect(() => { load() }, [filterType])

  // Mode éditeur plein écran
  if (editMode) {
    return (
      <div className="h-full">
        <TemplateEditorPanel
          template={editTemplate}
          onBack={handleBack}
          onSaved={onSaved}
        />
      </div>
    )
  }

  // Mode liste
  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Templates de documents</h1>
          <p className="text-sm text-gray-500 mt-1">
            Personnalisez vos avis d'échéance, quittances et courriers
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={initDefaults} disabled={initLoading}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50">
            {initLoading ? <RefreshCw size={15} className="animate-spin" /> : <Download size={15} />}
            Modèles par défaut
          </button>
          <button onClick={openNew}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={15} />
            Nouveau template
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 flex items-center gap-2">
          <Check size={14} className="text-green-600" /> {successMsg}
        </div>
      )}

      {/* Filtres */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {[{ value: '', label: 'Tous' }, ...TEMPLATE_TYPES].map(t => (
          <button key={t.value} onClick={() => setFilterType(t.value)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              filterType === t.value
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Liste */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Chargement…</div>
      ) : templates.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <FileText size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium mb-1">Aucun template configuré</p>
          <p className="text-sm text-gray-400 mb-4">Commencez par charger les modèles par défaut ou créez le vôtre.</p>
          <button onClick={initDefaults}
            className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Charger les modèles par défaut
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map(t => (
            <div key={t.id} className="bg-white rounded-xl border overflow-hidden hover:shadow-md transition-shadow">
              {/* Bande couleur + logo */}
              <div style={{ backgroundColor: t.header_color ?? '#1E3A5F' }}
                className="h-12 flex items-center px-4 gap-3">
                {t.logo_url && (
                  <img src={`${API_BASE}${t.logo_url}`} alt="logo"
                    className="h-8 w-auto max-w-[80px] object-contain" />
                )}
                <span className="text-white text-sm font-semibold truncate">
                  {t.company_name || t.name}
                </span>
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-900 text-sm truncate flex items-center gap-1.5">
                      {t.name}
                      {t.is_default && <Star size={12} className="fill-yellow-400 text-yellow-400 shrink-0" />}
                    </p>
                    <span className="text-xs text-blue-600 font-medium">{typeLabel(t.template_type)}</span>
                  </div>
                </div>

                {t.company_name && (
                  <p className="text-xs text-gray-500 mt-1 truncate">{t.company_name}</p>
                )}

                <div className="flex items-center justify-end mt-3 pt-3 border-t border-gray-100 gap-1">
                  <button onClick={() => openEdit(t)} title="Modifier"
                    className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                    <Pencil size={14} />
                  </button>
                  {!t.is_default && (
                    <button onClick={() => deleteTemplate(t)} title="Supprimer"
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
