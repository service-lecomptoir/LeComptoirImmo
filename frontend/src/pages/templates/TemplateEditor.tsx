import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import {
  FileText, Plus, Trash2, Edit2, Star, Upload,
  Eye, Check, Building2, Download
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TEMPLATE_TYPES = [
  { value: 'avis_echeance', label: "Avis d'échéance" },
  { value: 'quittance', label: 'Quittance de loyer' },
  { value: 'lettre_relance', label: 'Lettre de relance' },
  { value: 'lettre_resiliation', label: 'Lettre de résiliation' },
  { value: 'contrat_bail', label: 'Contrat de bail' },
  { value: 'etat_des_lieux', label: 'État des lieux' },
]

const VARIABLES = [
  { var: '{{tenant_name}}', desc: 'Nom du locataire' },
  { var: '{{property_name}}', desc: 'Nom du bien' },
  { var: '{{unit_ref}}', desc: 'Référence unité' },
  { var: '{{property_address}}', desc: 'Adresse du bien' },
  { var: '{{rent_amount}}', desc: 'Montant loyer' },
  { var: '{{charges_amount}}', desc: 'Montant charges' },
  { var: '{{total_due}}', desc: 'Total à payer' },
  { var: '{{amount_paid}}', desc: 'Montant reçu' },
  { var: '{{due_date}}', desc: "Date d'échéance" },
  { var: '{{month}}', desc: 'Mois concerné' },
  { var: '{{date}}', desc: 'Date du jour' },
  { var: '{{company_name}}', desc: 'Nom société' },
  { var: '{{apl_amount}}', desc: 'Aide au logement' },
]

interface Template {
  id: string
  name: string
  template_type: string
  logo_url?: string
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

interface TemplateFormProps {
  template?: Template | null
  onClose: () => void
  onSaved: () => void
}

function TemplateForm({ template, onClose, onSaved }: TemplateFormProps) {
  const { accessToken: token } = useAuthStore()
  const [form, setForm] = useState({
    name: template?.name || '',
    template_type: template?.template_type || 'avis_echeance',
    header_color: template?.header_color || '#1E3A5F',
    company_name: template?.company_name || '',
    company_address: template?.company_address || '',
    company_phone: template?.company_phone || '',
    company_email: template?.company_email || '',
    company_siret: template?.company_siret || '',
    content_html: template?.content_html || '',
    footer_text: template?.footer_text || '',
    is_default: template?.is_default || false,
    is_active: template?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [preview, setPreview] = useState(false)
  const [tab, setTab] = useState<'general' | 'content' | 'logo'>('general')
  const [savedId, setSavedId] = useState<string | null>(template?.id || null)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      let id = savedId
      if (template?.id) {
        await axios.patch(`${API}/api/v1/templates/${template.id}`, form, {
          headers: { Authorization: `Bearer ${token}` }
        })
        id = template.id
      } else {
        const r = await axios.post(`${API}/api/v1/templates`, form, {
          headers: { Authorization: `Bearer ${token}` }
        })
        id = r.data.id
        setSavedId(id)
      }

      // Upload logo si sélectionné
      if (logoFile && id) {
        const fd = new FormData()
        fd.append('file', logoFile)
        await axios.post(`${API}/api/v1/templates/${id}/upload-logo`, fd, {
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'multipart/form-data' }
        })
      }

      onSaved()
      onClose()
    } catch {
      alert('Erreur lors de la sauvegarde')
    } finally {
      setSaving(false)
    }
  }

  const insertVariable = (v: string) => {
    const ta = document.getElementById('template-content') as HTMLTextAreaElement
    if (ta) {
      const start = ta.selectionStart
      const end = ta.selectionEnd
      const newContent = form.content_html.slice(0, start) + v + form.content_html.slice(end)
      setForm({ ...form, content_html: newContent })
      setTimeout(() => {
        ta.focus()
        ta.setSelectionRange(start + v.length, start + v.length)
      }, 0)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">
        <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
          <h2 className="text-lg font-bold text-gray-900">
            {template ? 'Modifier le template' : 'Nouveau template'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b shrink-0">
          {(['general', 'content', 'logo'] as const).map(t => (
            <button key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'general' ? 'Informations' : t === 'content' ? 'Contenu HTML' : 'Logo & Couleurs'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="p-6">
            {tab === 'general' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Nom du template *</label>
                    <input required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.name}
                      onChange={e => setForm({ ...form, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Type de document</label>
                    <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.template_type}
                      onChange={e => setForm({ ...form, template_type: e.target.value })}>
                      {TEMPLATE_TYPES.map(t => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nom de la société/cabinet</label>
                  <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.company_name}
                    onChange={e => setForm({ ...form, company_name: e.target.value })}
                    placeholder="Cabinet Immobilier XYZ" />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Adresse</label>
                  <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.company_address}
                    onChange={e => setForm({ ...form, company_address: e.target.value })} />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Téléphone</label>
                    <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.company_phone}
                      onChange={e => setForm({ ...form, company_phone: e.target.value })} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.company_email}
                      onChange={e => setForm({ ...form, company_email: e.target.value })} />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SIRET</label>
                  <input className="w-full border rounded-lg px-3 py-2 text-sm" value={form.company_siret}
                    onChange={e => setForm({ ...form, company_siret: e.target.value })} />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Pied de page</label>
                  <textarea rows={2} className="w-full border rounded-lg px-3 py-2 text-sm" value={form.footer_text}
                    onChange={e => setForm({ ...form, footer_text: e.target.value })} />
                </div>

                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={form.is_default}
                      onChange={e => setForm({ ...form, is_default: e.target.checked })} />
                    <span className="text-sm text-gray-700">Template par défaut pour ce type</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={form.is_active}
                      onChange={e => setForm({ ...form, is_active: e.target.checked })} />
                    <span className="text-sm text-gray-700">Actif</span>
                  </label>
                </div>
              </div>
            )}

            {tab === 'content' && (
              <div className="space-y-4">
                {/* Variables helper */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-xs font-medium text-blue-800 mb-2">Variables disponibles (cliquer pour insérer) :</p>
                  <div className="flex flex-wrap gap-1.5">
                    {VARIABLES.map(v => (
                      <button key={v.var} type="button"
                        onClick={() => insertVariable(v.var)}
                        title={v.desc}
                        className="text-xs px-2 py-0.5 bg-white border border-blue-200 rounded text-blue-700 hover:bg-blue-100 font-mono"
                      >
                        {v.var}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2 mb-2">
                  <button type="button"
                    onClick={() => setPreview(!preview)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                      preview ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Eye size={12} />
                    {preview ? 'Éditeur' : 'Aperçu HTML'}
                  </button>
                </div>

                {preview ? (
                  <div className="border rounded-lg p-4 min-h-64 bg-white">
                    <div
                      style={{ borderTop: `4px solid ${form.header_color}` }}
                      className="p-4 rounded"
                      dangerouslySetInnerHTML={{ __html: form.content_html || '<em class="text-gray-400">Aucun contenu</em>' }}
                    />
                    {form.footer_text && (
                      <div className="mt-4 pt-4 border-t text-xs text-gray-400">{form.footer_text}</div>
                    )}
                  </div>
                ) : (
                  <textarea
                    id="template-content"
                    rows={20}
                    className="w-full border rounded-lg px-3 py-2 text-xs font-mono"
                    placeholder="HTML du template... ex: <h2>AVIS D'ÉCHÉANCE</h2><p>Cher {{tenant_name}}...</p>"
                    value={form.content_html}
                    onChange={e => setForm({ ...form, content_html: e.target.value })}
                  />
                )}
              </div>
            )}

            {tab === 'logo' && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Couleur d'en-tête</label>
                  <div className="flex items-center gap-4">
                    <input type="color" value={form.header_color || '#1E3A5F'}
                      onChange={e => setForm({ ...form, header_color: e.target.value })}
                      className="w-12 h-10 rounded cursor-pointer" />
                    <input className="border rounded-lg px-3 py-2 text-sm w-32"
                      value={form.header_color || '#1E3A5F'}
                      onChange={e => setForm({ ...form, header_color: e.target.value })} />
                    <div className="flex gap-2">
                      {['#1E3A5F', '#F07800', '#059669', '#7C3AED', '#DC2626', '#1D4ED8'].map(c => (
                        <button key={c} type="button"
                          onClick={() => setForm({ ...form, header_color: c })}
                          className={`w-8 h-8 rounded-full border-2 ${form.header_color === c ? 'border-gray-800 scale-110' : 'border-transparent'}`}
                          style={{ backgroundColor: c }}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Logo</label>
                  <div
                    onClick={() => fileRef.current?.click()}
                    className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
                  >
                    {logoFile ? (
                      <div className="space-y-2">
                        <Check size={32} className="mx-auto text-green-500" />
                        <p className="text-sm font-medium text-gray-700">{logoFile.name}</p>
                        <p className="text-xs text-gray-400">Cliquer pour changer</p>
                      </div>
                    ) : template?.logo_url ? (
                      <div className="space-y-2">
                        <img src={`${API}${template.logo_url}`} alt="Logo" className="max-h-16 mx-auto object-contain" />
                        <p className="text-xs text-gray-400">Cliquer pour remplacer</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Upload size={32} className="mx-auto text-gray-400" />
                        <p className="text-sm font-medium text-gray-700">Déposer ou cliquer pour uploader</p>
                        <p className="text-xs text-gray-400">PNG, JPG, SVG — max 2Mo</p>
                      </div>
                    )}
                  </div>
                  <input ref={fileRef} type="file" accept="image/*" className="hidden"
                    onChange={e => setLogoFile(e.target.files?.[0] || null)} />
                </div>

                {/* Aperçu en-tête */}
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Aperçu de l'en-tête</p>
                  <div className="border rounded-lg overflow-hidden">
                    <div style={{ backgroundColor: form.header_color || '#1E3A5F' }} className="p-4 flex items-center gap-4">
                      {(logoFile || template?.logo_url) && (
                        <div className="w-12 h-12 bg-white rounded flex items-center justify-center">
                          {logoFile
                            ? <img src={URL.createObjectURL(logoFile)} alt="" className="max-h-10 object-contain" />
                            : <img src={`${API}${template?.logo_url}`} alt="" className="max-h-10 object-contain" />
                          }
                        </div>
                      )}
                      <div className="text-white">
                        <p className="font-bold">{form.company_name || 'Votre société'}</p>
                        <p className="text-xs opacity-75">{form.company_address || 'Votre adresse'}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="border-t p-4 flex gap-3 shrink-0">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg text-sm text-gray-700 hover:bg-gray-50">
              Annuler
            </button>
            <button type="submit" disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Sauvegarde...' : <><Check size={14} /> Enregistrer</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function TemplateEditor() {
  const { accessToken: token } = useAuthStore()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editTemplate, setEditTemplate] = useState<Template | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const params = filterType ? `?template_type=${filterType}` : ''
      const r = await axios.get(`${API}/api/v1/templates${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setTemplates(r.data)
    } catch {
      setTemplates([])
    }
    setLoading(false)
  }

  const initDefaults = async () => {
    await axios.post(`${API}/api/v1/templates/initialize-defaults`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    load()
  }

  useEffect(() => { load() }, [filterType])

  const deleteTemplate = async (id: string) => {
    if (!confirm('Supprimer ce template ?')) return
    try {
      await axios.delete(`${API}/api/v1/templates/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      load()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Erreur')
    }
  }

  const typeLabel = (val: string) => TEMPLATE_TYPES.find(t => t.value === val)?.label || val

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Templates de documents</h1>
          <p className="text-sm text-gray-500 mt-1">Personnalisez vos avis d'échéance, quittances et courriers</p>
        </div>
        <div className="flex gap-2">
          <button onClick={initDefaults}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50">
            <Download size={16} />
            Charger les modèles par défaut
          </button>
          <button onClick={() => { setEditTemplate(null); setShowModal(true) }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            <Plus size={16} />
            Nouveau template
          </button>
        </div>
      </div>

      {/* Filtre */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button onClick={() => setFilterType('')}
          className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${!filterType ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
          Tous
        </button>
        {TEMPLATE_TYPES.map(t => (
          <button key={t.value} onClick={() => setFilterType(t.value)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${filterType === t.value ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Chargement…</div>
      ) : templates.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <FileText size={48} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 mb-3">Aucun template configuré</p>
          <button onClick={initDefaults}
            className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Charger les modèles par défaut
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map(t => (
            <div key={t.id} className="bg-white rounded-xl border overflow-hidden hover:shadow-md transition-shadow">
              {/* Preview bar */}
              <div style={{ backgroundColor: t.header_color || '#1E3A5F' }} className="h-2" />
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-gray-900 text-sm">{t.name}</p>
                      {t.is_default && (
                        <Star size={12} className="fill-yellow-400 text-yellow-400" />
                      )}
                    </div>
                    <span className="text-xs text-gray-500">{typeLabel(t.template_type)}</span>
                  </div>
                  {t.logo_url && (
                    <img src={`${API}${t.logo_url}`} alt="logo" className="h-8 object-contain" />
                  )}
                </div>

                {t.company_name && (
                  <div className="flex items-center gap-1 text-xs text-gray-500 mt-2">
                    <Building2 size={10} />
                    <span>{t.company_name}</span>
                  </div>
                )}

                <div className="flex items-center justify-between mt-3 pt-3 border-t">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: t.header_color || '#1E3A5F' }} />
                    <span className="text-xs text-gray-400">{t.header_color}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => { setEditTemplate(t); setShowModal(true) }}
                      className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg">
                      <Edit2 size={14} />
                    </button>
                    {!t.is_default && (
                      <button onClick={() => deleteTemplate(t.id)}
                        className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg">
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
        <TemplateForm template={editTemplate} onClose={() => setShowModal(false)} onSaved={load} />
      )}
    </div>
  )
}
