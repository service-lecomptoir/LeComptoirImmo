import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ArrowLeft, Save, X, Star, Check, RefreshCw,
  Trash2, Pencil, Image as ImageIcon, FileText, GripHorizontal,
} from 'lucide-react'
import { apiClient } from '@/api/client'
import { useAuthStore } from '@/store/authStore'
import RichTextEditor, { type RichTextEditorHandle } from '@/components/common/RichTextEditor'
import AvisBlockEditor from './AvisBlockEditor'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Découpe l'adresse du profil en lignes (n° et rue / code postal Ville).
const addressLines = (addr?: string | null): string[] =>
  (addr ?? '').split(/[\n,]+/).map(s => s.trim()).filter(Boolean)

// ── Constantes ────────────────────────────────────────────────────────────────

const TEMPLATE_TYPES = [
  { value: 'avis_echeance',           label: "Avis d'échéance" },
  { value: 'quittance',               label: 'Quittance de loyer' },
  { value: 'regularisation_charges',  label: 'Régularisation de charges locatives' },
  { value: 'revision_loyer',          label: 'Révision loyer' },
  { value: 'taxes_foncieres',         label: 'Décompte Taxes Foncières' },
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
      { key: '{{property_name}}', label: 'Bien' },
      { key: '{{unit_ref}}', label: 'Référence du bien' },
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
      { key: '{{lease_start_date}}', label: "Date d'entrée" },
      { key: '{{date}}', label: "Date du jour" },
    ],
  },
  {
    label: 'Gestionnaire', color: '#374151', bg: '#f3f4f6', text: '#111827',
    vars: [
      { key: '{{company_name}}', label: 'Nom gestionnaire' },
    ],
  },
]

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
  blocks?: any[] | null
  theme?: Record<string, string> | null
  logo_url?: string | null
  is_default: boolean
  is_active: boolean
}

interface FormData {
  name: string
  template_type: string
  header_color: string
  content_html: string
  footer_text: string
  is_default: boolean
}

// Contenu de départ par type — pour que changer de type produise un effet visible.
const DEFAULT_CONTENT: Record<string, string> = {
  avis_echeance:
    "Cher(e) {{tenant_name}},\n\nNous vous informons que le loyer du bien {{property_name}} ({{property_address}}) " +
    "pour le mois de {{month}} s'élève à {{total_due}} € (loyer {{rent_amount}} € + charges {{charges_amount}} €).\n" +
    "Merci de bien vouloir procéder au règlement avant le {{due_date}}.\n\nCordialement,\n{{company_name}}",
  quittance:
    "Quittance de loyer — {{month}}\n\nJe soussigné(e) {{company_name}}, atteste que {{tenant_name}} s'est acquitté(e) " +
    "de la somme de {{amount_paid}} € pour le bien {{property_name}} ({{property_address}}).\n\n" +
    "Fait pour valoir ce que de droit.\nLe {{date}}",
  lettre_relance:
    "Cher(e) {{tenant_name}},\n\nSauf erreur de notre part, le loyer du mois de {{month}} ({{total_due}} €) pour " +
    "{{property_name}} demeure impayé à ce jour.\nNous vous remercions de régulariser votre situation dans les meilleurs délais.\n\n" +
    "Cordialement,\n{{company_name}}",
  lettre_resiliation:
    "Cher(e) {{tenant_name}},\n\nLa présente fait suite au bail portant sur le bien {{property_name}} ({{property_address}}).\n\n" +
    "Le {{date}}\n{{company_name}}",
  contrat_bail:
    "Contrat de bail — {{property_name}}\n\nEntre {{company_name}} (bailleur) et {{tenant_name}} (locataire), " +
    "pour le bien situé {{property_address}}.\nLoyer mensuel : {{rent_amount}} € + charges {{charges_amount}} €.\n\nLe {{date}}",
  etat_des_lieux:
    "État des lieux — {{property_name}}\n\nBien : {{property_address}}\nLocataire : {{tenant_name}}\nDate : {{date}}\n\n" +
    "(Décrivez l'état de chaque pièce.)",
}

const EMPTY_FORM: FormData = {
  name: '', template_type: 'avis_echeance', header_color: '#1E3A5F',
  content_html: DEFAULT_CONTENT.avis_echeance, footer_text: '', is_default: false,
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
      content_html: template.content_html ?? '',
      footer_text: template.footer_text ?? '',
      is_default: template.is_default,
    } : { ...EMPTY_FORM }
  )

  const currentUser = useAuthStore(s => s.user)
  const fetchMe = useAuthStore(s => s.fetchMe)

  // Garde l'« Émetteur » à jour : rafraîchit le profil à l'ouverture de l'éditeur,
  // et chaque fois que l'onglet reprend le focus (couvre le cas où l'utilisateur
  // modifie « Mes informations » dans un autre onglet).
  useEffect(() => {
    fetchMe()
    const onFocus = () => { fetchMe() }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [fetchMe])

  const [logoPreview, setLogoPreview] = useState<string | null>(
    template?.logo_url ? `${API_BASE}${template.logo_url}` : null
  )
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // ── Mise en page (globale) + aperçu PDF réel ───────────────────────────────
  const [layout, setLayout] = useState<any>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewErr, setPreviewErr] = useState('')
  const previewUrlRef = useRef<string | null>(null)

  // Charge la configuration de mise en page (commune à tous les documents).
  useEffect(() => {
    apiClient.get('/settings/template-layout')
      .then(r => setLayout(r.data))
      .catch(() => setLayout({ spacing: { page_margin: '2cm 2.5cm', line_height: 1.55, font_size: 10 } }))
  }, [])

  // Persiste la mise en page (débauché) dès qu'elle change.
  useEffect(() => {
    if (!layout) return
    const h = setTimeout(() => { apiClient.put('/settings/template-layout', layout).catch(() => {}) }, 900)
    return () => clearTimeout(h)
  }, [layout])

  const setSpacing = (key: string, value: number | string) =>
    setLayout((l: any) => ({ ...(l || {}), spacing: { ...((l || {}).spacing || {}), [key]: value } }))

  const editorRef = useRef<RichTextEditorHandle>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const set = (field: keyof FormData, value: string | boolean) =>
    setForm(f => ({ ...f, [field]: value }))

  // Génère (débauché) l'aperçu PDF RÉEL du brouillon, identique au document final.
  useEffect(() => {
    if (!layout) return
    let cancelled = false
    const h = setTimeout(async () => {
      setPreviewLoading(true); setPreviewErr('')
      try {
        const r = await apiClient.post('/templates/preview', {
          template_type: form.template_type,
          content_html: form.content_html,
          footer_text: form.footer_text,
          header_color: form.header_color,
          template_id: template?.id ?? null,
          layout,
        }, { responseType: 'blob' })
        if (cancelled) return
        const url = URL.createObjectURL(r.data as Blob)
        if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
        previewUrlRef.current = url
        setPreviewUrl(url)
      } catch {
        if (!cancelled) setPreviewErr("Aperçu indisponible (vérifiez le contenu).")
      } finally {
        if (!cancelled) setPreviewLoading(false)
      }
    }, 700)
    return () => { cancelled = true; clearTimeout(h) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout, form.content_html, form.footer_text, form.header_color, form.template_type, template?.id,
      currentUser?.full_name, currentUser?.address])

  // Libère l'URL blob au démontage.
  useEffect(() => () => { if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current) }, [])

  // Changer le type : remplace le contenu par le starter du type tant que
  // l'utilisateur n'a pas écrit son propre contenu (vide ou starter connu).
  const STARTERS = Object.values(DEFAULT_CONTENT)
  const changeType = (newType: string) =>
    setForm(f => {
      const replaceable = !f.content_html?.trim() || STARTERS.includes(f.content_html)
      return {
        ...f,
        template_type: newType,
        content_html: replaceable ? (DEFAULT_CONTENT[newType] ?? '') : f.content_html,
      }
    })

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

  // ── Insertion de variable (clic) + drag & drop ──────────────────────────────

  const insertVar = useCallback((varKey: string) => {
    editorRef.current?.insertText(varKey)
  }, [])

  const handleVarDragStart = (e: React.DragEvent, varKey: string) => {
    e.dataTransfer.setData('text/plain', varKey)
    e.dataTransfer.effectAllowed = 'copy'
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

        <span className="text-xs font-medium px-2.5 py-1.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-100 shrink-0">
          {typeLabel(form.template_type)}
        </span>

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

        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 shrink-0 transition-colors">
          {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
          <span>Enregistrer</span>
        </button>
      </div>

      {/* ── Bannière d'erreur ─────────────────────────────────────────────── */}
      {error && (
        <div className="shrink-0 px-4 py-2 bg-red-50 border-b border-red-200 flex items-center gap-2 text-sm text-red-700">
          <X size={14} className="shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Corps principal ────────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">

        {/* ── Colonne gauche : paramètres ─────────────────────────────────── */}
        <div className="w-72 shrink-0 border-r overflow-y-auto bg-gray-50">
          <div className="p-4 space-y-5">

            {/* Type de document (modifiable uniquement à la création) */}
            {!template && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Type de document</p>
                <select className={inp} value={form.template_type} onChange={e => changeType(e.target.value)}>
                  {TEMPLATE_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                <p className="text-xs text-gray-400 mt-1">Choisissez le type : un contenu de départ est pré-rempli.</p>
              </div>
            )}

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

            {/* Émetteur : Nom + adresse du gestionnaire (issus du profil, sous le logo) */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Émetteur</p>
              <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm">
                <p className="font-semibold text-gray-800">{currentUser?.full_name || 'Votre nom'}</p>
                {addressLines(currentUser?.address).length > 0 ? (
                  addressLines(currentUser?.address).map((l, i) => (
                    <p key={i} className="text-xs text-gray-500">{l}</p>
                  ))
                ) : (
                  <p className="text-xs text-gray-400 italic">Adresse non renseignée</p>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
                Le nom et l'adresse proviennent de votre profil et s'affichent automatiquement
                sous le logo. Pour les modifier, rendez-vous dans « Mes informations ».
              </p>
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
              <span className="text-xs text-gray-400">Mettez en forme le texte ; glissez les marqueurs dedans</span>
            </div>

            <div className="flex-1 min-h-0 rounded-xl border-2 border-gray-200 overflow-hidden">
              <RichTextEditor
                ref={editorRef}
                html={form.content_html}
                onChange={v => set('content_html', v)}
              />
            </div>
          </div>
        </div>

        {/* ── Colonne droite : mise en page + aperçu PDF RÉEL ──────────────── */}
        <div className="w-[420px] shrink-0 bg-gray-100 flex flex-col overflow-hidden">

          {/* Barre de mise en page (s'applique à tous les documents) */}
          <div className="shrink-0 px-3 py-2 border-b bg-white flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] text-gray-500">Police</label>
              <select value={layout?.spacing?.font_family ?? 'Helvetica, Arial, sans-serif'}
                onChange={e => setSpacing('font_family', e.target.value)}
                className="text-xs border border-gray-200 rounded px-1.5 py-1 bg-gray-50 max-w-[120px]">
                <option value="Helvetica, Arial, sans-serif">Helvetica</option>
                <option value="Arial, sans-serif">Arial</option>
                <option value='Georgia, "Times New Roman", serif'>Georgia</option>
                <option value='"Times New Roman", Times, serif'>Times</option>
                <option value="Verdana, sans-serif">Verdana</option>
                <option value='"Trebuchet MS", sans-serif'>Trebuchet</option>
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] text-gray-500">Taille</label>
              <select value={layout?.spacing?.font_size ?? 10}
                onChange={e => setSpacing('font_size', Number(e.target.value))}
                className="text-xs border border-gray-200 rounded px-1.5 py-1 bg-gray-50">
                {[8, 9, 10, 11, 12].map(s => <option key={s} value={s}>{s} pt</option>)}
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] text-gray-500">Interligne</label>
              <select value={layout?.spacing?.line_height ?? 1.55}
                onChange={e => setSpacing('line_height', Number(e.target.value))}
                className="text-xs border border-gray-200 rounded px-1.5 py-1 bg-gray-50">
                {[1.3, 1.45, 1.55, 1.7, 1.9].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] text-gray-500">Paragraphes</label>
              <select value={layout?.spacing?.paragraph_spacing ?? 8}
                onChange={e => setSpacing('paragraph_spacing', Number(e.target.value))}
                className="text-xs border border-gray-200 rounded px-1.5 py-1 bg-gray-50">
                <option value={4}>Compact</option>
                <option value={8}>Normal</option>
                <option value={12}>Aéré</option>
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <label className="text-[11px] text-gray-500">Marges</label>
              <select value={layout?.spacing?.page_margin ?? '2cm 2.5cm'}
                onChange={e => setSpacing('page_margin', e.target.value)}
                className="text-xs border border-gray-200 rounded px-1.5 py-1 bg-gray-50">
                <option value="1.5cm 2cm">Serrées</option>
                <option value="2cm 2.5cm">Normales</option>
                <option value="2.5cm 3cm">Aérées</option>
              </select>
            </div>
          </div>

          {/* Aperçu : le vrai PDF généré côté serveur */}
          <div className="flex items-center justify-between px-3 py-1.5 shrink-0">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Aperçu document</p>
            <span className="text-xs text-gray-400 flex items-center gap-1">
              {previewLoading ? <><RefreshCw size={11} className="animate-spin" /> génération…</> : 'PDF final'}
            </span>
          </div>
          <div className="flex-1 min-h-0 px-3 pb-3">
            <div className="w-full h-full rounded-lg border border-gray-200 bg-white overflow-hidden relative">
              {previewErr ? (
                <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-400 px-4 text-center">{previewErr}</div>
              ) : previewUrl ? (
                <iframe title="Aperçu PDF" src={`${previewUrl}#toolbar=0&navpanes=0`} className="w-full h-full" />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-400">
                  <RefreshCw size={14} className="animate-spin mr-2" /> Préparation de l'aperçu…
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}

// ── Page liste des templates ──────────────────────────────────────────────────

export default function TemplateEditor() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [editTemplate, setEditTemplate] = useState<Template | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const triggerReload = () => setReloadKey(k => k + 1)

  const deleteTemplate = async (t: Template) => {
    if (!confirm(`Supprimer "${t.name}" ?`)) return
    try {
      await apiClient.delete(`/templates/${t.id}`)
      triggerReload()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la suppression')
    }
  }

  const openEdit = (t: Template) => { setEditTemplate(t); setEditMode(true) }
  const handleBack = () => { setEditMode(false); setEditTemplate(null) }
  const onSaved = () => { setSuccessMsg('Template enregistré'); setTimeout(() => setSuccessMsg(''), 3000); triggerReload() }

  useEffect(() => {
    if (editMode) return
    let cancelled = false
    setLoading(true)
    apiClient.get<Template[]>('/templates')
      .then(r => { if (!cancelled) { setTemplates(r.data); setLoading(false) } })
      .catch(() => { if (!cancelled) { setTemplates([]); setLoading(false) } })
    return () => { cancelled = true }
  }, [editMode, reloadKey])

  // Mode éditeur plein écran
  if (editMode) {
    // Tout document doté de blocs → éditeur par blocs (mise en page moderne).
    const useBlockEditor =
      Array.isArray(editTemplate?.blocks) && (editTemplate?.blocks?.length ?? 0) > 0
    return (
      <div className="fixed inset-0 z-50 overflow-hidden">
        {useBlockEditor ? (
          <AvisBlockEditor
            key={editTemplate!.id}
            template={editTemplate as any}
            onBack={handleBack}
            onSaved={onSaved}
          />
        ) : (
          <TemplateEditorPanel
            key={editTemplate?.id ?? 'new'}
            template={editTemplate}
            onBack={handleBack}
            onSaved={onSaved}
          />
        )}
      </div>
    )
  }

  // Mode liste
  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Ma papeterie</h1>
        <p className="text-sm text-gray-500 mt-1">
          Personnalisez vos documents — avis d'échéance, quittances, régularisations de charges, révisions de loyer et décomptes de taxes foncières — en cliquant sur l'un des modèles ci-dessous.
        </p>
      </div>

      {successMsg && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800 flex items-center gap-2">
          <Check size={14} className="text-green-600" /> {successMsg}
        </div>
      )}

      {/* Liste */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Chargement…</div>
      ) : templates.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <FileText size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium mb-1">Aucun template configuré</p>
          <p className="text-sm text-gray-400">Vos modèles par défaut seront recréés au prochain démarrage du serveur.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map(t => (
            <div key={t.id} className="bg-white rounded-xl border overflow-hidden hover:shadow-md transition-shadow">
              {/* Bande couleur (le logo vient du profil « Mes informations », pas du modèle) */}
              <div style={{ backgroundColor: t.header_color ?? '#1E3A5F' }}
                className="h-12 flex items-center px-4 gap-3">
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
