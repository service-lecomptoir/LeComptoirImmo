import { useState, useEffect } from 'react'
import { FileText, Plus, Trash2, Pencil, Star, Check, X, RefreshCw, Download } from 'lucide-react'
import { apiClient } from '@/api/client'

// ── Constantes ────────────────────────────────────────────────────────────────

const TEMPLATE_TYPES = [
  { value: 'avis_echeance',      label: "Avis d'échéance" },
  { value: 'quittance',          label: 'Quittance de loyer' },
  { value: 'lettre_relance',     label: 'Lettre de relance' },
  { value: 'lettre_resiliation', label: 'Lettre de résiliation' },
  { value: 'contrat_bail',       label: 'Contrat de bail' },
  { value: 'etat_des_lieux',     label: 'État des lieux' },
]

const PRESET_COLORS = [
  '#1E3A5F', '#2563EB', '#059669', '#D97706', '#7C3AED', '#DC2626', '#374151',
]

const VARIABLES = [
  '{{tenant_name}}', '{{property_name}}', '{{unit_ref}}', '{{property_address}}',
  '{{rent_amount}}', '{{charges_amount}}', '{{total_due}}', '{{amount_paid}}',
  '{{due_date}}', '{{month}}', '{{date}}', '{{company_name}}', '{{apl_amount}}',
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
  is_default: boolean
  is_active: boolean
}

type FormData = Omit<Template, 'id' | 'is_active'>

const EMPTY_FORM: FormData = {
  name: '',
  template_type: 'avis_echeance',
  header_color: '#1E3A5F',
  company_name: '',
  company_address: '',
  company_phone: '',
  company_email: '',
  company_siret: '',
  content_html: '',
  footer_text: '',
  is_default: false,
}

// ── Modale Formulaire ─────────────────────────────────────────────────────────

function TemplateModal({
  template,
  onClose,
  onSaved,
}: {
  template: Template | null
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState<FormData>(
    template
      ? {
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
        }
      : { ...EMPTY_FORM }
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (field: keyof FormData, value: string | boolean) =>
    setForm(f => ({ ...f, [field]: value }))

  const handleSave = async () => {
    if (!form.name.trim()) { setError('Le nom est obligatoire'); return }
    setSaving(true); setError('')
    try {
      if (template?.id) {
        await apiClient.patch(`/templates/${template.id}`, form)
      } else {
        await apiClient.post('/templates', form)
      }
      onSaved()
      onClose()
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail) || 'Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const insertVar = (v: string) => {
    const ta = document.getElementById('tpl-content') as HTMLTextAreaElement | null
    if (!ta) { set('content_html', (form.content_html ?? '') + v); return }
    const s = ta.selectionStart, e = ta.selectionEnd
    const next = (form.content_html ?? '').slice(0, s) + v + (form.content_html ?? '').slice(e)
    set('content_html', next)
    setTimeout(() => { ta.focus(); ta.setSelectionRange(s + v.length, s + v.length) }, 0)
  }

  const inp = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
          <h2 className="text-lg font-bold text-gray-900">
            {template ? 'Modifier le template' : 'Nouveau template'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Body scrollable */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">

          {/* Nom + Type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Nom *</label>
              <input className={inp} value={form.name} onChange={e => set('name', e.target.value)}
                placeholder="Ex: Avis d'échéance standard" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Type de document</label>
              <select className={inp} value={form.template_type}
                onChange={e => set('template_type', e.target.value)}>
                {TEMPLATE_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Informations cabinet */}
          <div className="border border-gray-200 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Votre cabinet</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Nom société</label>
                <input className={inp} value={form.company_name}
                  onChange={e => set('company_name', e.target.value)}
                  placeholder="Cabinet Immobilier XYZ" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">SIRET</label>
                <input className={inp} value={form.company_siret}
                  onChange={e => set('company_siret', e.target.value)} placeholder="12345678900000" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Adresse</label>
              <input className={inp} value={form.company_address}
                onChange={e => set('company_address', e.target.value)}
                placeholder="1 rue de la Paix, 75001 Paris" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Téléphone</label>
                <input className={inp} value={form.company_phone}
                  onChange={e => set('company_phone', e.target.value)} placeholder="01 23 45 67 89" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Email</label>
                <input type="email" className={inp} value={form.company_email}
                  onChange={e => set('company_email', e.target.value)} placeholder="contact@cabinet.fr" />
              </div>
            </div>
          </div>

          {/* Couleur d'en-tête */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Couleur d'en-tête</label>
            <div className="flex items-center gap-2">
              {PRESET_COLORS.map(c => (
                <button key={c} type="button"
                  onClick={() => set('header_color', c)}
                  className={`w-8 h-8 rounded-full border-2 transition-transform ${
                    form.header_color === c ? 'border-gray-800 scale-110' : 'border-white shadow'
                  }`}
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
              <input type="color" value={form.header_color ?? '#1E3A5F'}
                onChange={e => set('header_color', e.target.value)}
                className="w-8 h-8 rounded cursor-pointer border border-gray-200"
                title="Couleur personnalisée" />
            </div>
            {/* Mini aperçu */}
            <div className="mt-2 rounded-lg overflow-hidden border border-gray-200 flex items-center gap-3 px-4 py-2"
              style={{ backgroundColor: form.header_color ?? '#1E3A5F' }}>
              <span className="text-white text-sm font-semibold">
                {form.company_name || 'Votre société'}
              </span>
            </div>
          </div>

          {/* Contenu */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-medium text-gray-700">Contenu du document</label>
            </div>
            {/* Variables rapides */}
            <div className="flex flex-wrap gap-1 mb-2">
              {VARIABLES.map(v => (
                <button key={v} type="button" onClick={() => insertVar(v)}
                  className="text-xs px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-gray-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 font-mono">
                  {v}
                </button>
              ))}
            </div>
            <textarea
              id="tpl-content"
              rows={8}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              placeholder="Saisissez le contenu HTML ou texte du document. Cliquez sur une variable pour l'insérer."
              value={form.content_html}
              onChange={e => set('content_html', e.target.value)}
            />
          </div>

          {/* Pied de page */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Pied de page</label>
            <input className={inp} value={form.footer_text}
              onChange={e => set('footer_text', e.target.value)}
              placeholder="Texte légal, mentions obligatoires…" />
          </div>

          {/* Options */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.is_default}
              onChange={e => set('is_default', e.target.checked)} className="rounded" />
            <span className="text-sm text-gray-700">Template par défaut pour ce type de document</span>
          </label>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 flex gap-3 shrink-0">
          <button type="button" onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50">
            Annuler
          </button>
          <button type="button" onClick={handleSave} disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
            {saving ? <><RefreshCw size={14} className="animate-spin" /> Sauvegarde…</> : <><Check size={14} /> Enregistrer</>}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function TemplateEditor() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editTemplate, setEditTemplate] = useState<Template | null>(null)
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
      load()
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
      load()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Erreur lors de la suppression')
    }
  }

  const openNew = () => { setEditTemplate(null); setShowModal(true) }
  const openEdit = (t: Template) => { setEditTemplate(t); setShowModal(true) }

  const onSaved = () => {
    load()
    setSuccessMsg('Template enregistré')
    setTimeout(() => setSuccessMsg(''), 3000)
  }

  useEffect(() => { load() }, [filterType])

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

      {/* Filtres par type */}
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
          <p className="text-sm text-gray-400 mb-4">
            Commencez par charger les modèles par défaut ou créez le vôtre.
          </p>
          <button onClick={initDefaults}
            className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Charger les modèles par défaut
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map(t => (
            <div key={t.id} className="bg-white rounded-xl border overflow-hidden hover:shadow-md transition-shadow">
              {/* Bande couleur */}
              <div style={{ backgroundColor: t.header_color ?? '#1E3A5F' }} className="h-2" />
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

                <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full border border-gray-200"
                      style={{ backgroundColor: t.header_color ?? '#1E3A5F' }} />
                    <span className="text-xs text-gray-400">{t.header_color}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => openEdit(t)}
                      title="Modifier"
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg">
                      <Pencil size={14} />
                    </button>
                    {!t.is_default && (
                      <button onClick={() => deleteTemplate(t)}
                        title="Supprimer"
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <TemplateModal
          template={editTemplate}
          onClose={() => setShowModal(false)}
          onSaved={onSaved}
        />
      )}
    </div>
  )
}
