import { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, Check, Globe, Mail, MessageSquare } from 'lucide-react'
import { apiClient } from '@/api/client'
import { toast } from '@/store/toast'
import { Button } from '@/components/ui'

// Types de courrier (envoyés au locataire). Le rapport mensuel (gestionnaire) et
// la communication groupée n'en font pas partie.
const COMM_TYPES = [
  { value: 'avis_echeance', label: "Avis d'échéance" },
  { value: 'quittance', label: 'Quittance de loyer' },
  { value: 'rappel_impaye', label: 'Rappel impayé' },
  { value: 'relance_1', label: 'Relance' },
  { value: 'relance_2', label: 'Mise en demeure' },
  { value: 'revision_loyer', label: 'Révision du loyer' },
  { value: 'revision_charges', label: 'Révision des charges' },
  { value: 'taxe_om', label: "Taxe d'ordures ménagères" },
]
const LANGS = [
  { code: 'fr', label: 'Français' },
  { code: 'en', label: 'Anglais' },
  { code: 'pt-BR', label: 'Portugais (Brésil)' },
  { code: 'ht', label: 'Créole haïtien' },
  { code: 'srn', label: 'Sranan Tongo' },
]
const LANG_LABEL: Record<string, string> = Object.fromEntries(LANGS.map(l => [l.code, l.label]))

interface Tpl {
  id: string
  rule_type: string
  name: string
  content: Record<string, { subject?: string; body?: string; sms?: string }>
  is_selected: boolean
  is_active: boolean
}

const PLACEHOLDERS = '{{tenant_name}}, {{period}}, {{amount}}, {{due_date}}, {{property_name}}'

function TemplateModal({ ruleType, tpl, onClose, onSaved }: {
  ruleType: string, tpl: Tpl | null, onClose: () => void, onSaved: () => void,
}) {
  const [name, setName] = useState(tpl?.name || '')
  const [content, setContent] = useState<Record<string, any>>(tpl?.content || { fr: { subject: '', body: '', sms: '' } })
  const [saving, setSaving] = useState(false)

  const langOn = (code: string) => code in content
  const toggleLang = (code: string) => setContent(c => {
    const next = { ...c }
    if (code in next) delete next[code]
    else next[code] = { subject: '', body: '', sms: '' }
    return next
  })
  const setField = (code: string, field: string, value: string) =>
    setContent(c => ({ ...c, [code]: { ...c[code], [field]: value } }))

  const save = async () => {
    if (!name.trim()) { toast.error('Donnez un nom au modèle.'); return }
    if (Object.keys(content).length === 0) { toast.error('Cochez au moins une langue.'); return }
    setSaving(true)
    try {
      if (tpl) await apiClient.patch(`/message-templates/${tpl.id}`, { name, content })
      else await apiClient.post('/message-templates', { rule_type: ruleType, name, content })
      toast.success('Modèle enregistré')
      onSaved(); onClose()
    } catch { /* toast via intercepteur */ } finally { setSaving(false) }
  }

  const typeLabel = COMM_TYPES.find(t => t.value === ruleType)?.label || ruleType
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">
            {tpl ? 'Modifier le modèle' : 'Nouveau modèle'} · {typeLabel}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom du modèle *</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" value={name}
              onChange={e => setName(e.target.value)} placeholder="ex : Avis standard, Avis ton ferme…" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Langues</label>
            <div className="flex flex-wrap gap-2">
              {LANGS.map(l => (
                <button key={l.code} type="button" onClick={() => toggleLang(l.code)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${
                    langOn(l.code) ? 'bg-brand-navy text-white border-brand-navy' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}>
                  {langOn(l.code) && <Check size={13} />}{l.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-1">Variables : {PLACEHOLDERS}</p>
          </div>

          {Object.keys(content).map(code => (
            <div key={code} className="border border-gray-200 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-brand-navy">
                <Globe size={14} /> {LANG_LABEL[code] || code}
              </div>
              <div>
                <label className="flex items-center gap-1.5 text-xs font-medium text-gray-600 mb-1"><Mail size={12} /> Objet de l'e-mail</label>
                <input className="w-full border rounded-lg px-3 py-2 text-sm" value={content[code]?.subject || ''}
                  onChange={e => setField(code, 'subject', e.target.value)} />
              </div>
              <div>
                <label className="flex items-center gap-1.5 text-xs font-medium text-gray-600 mb-1"><Mail size={12} /> Corps de l'e-mail</label>
                <textarea rows={4} className="w-full border rounded-lg px-3 py-2 text-sm" value={content[code]?.body || ''}
                  onChange={e => setField(code, 'body', e.target.value)} />
              </div>
              <div>
                <label className="flex items-center gap-1.5 text-xs font-medium text-gray-600 mb-1"><MessageSquare size={12} /> SMS (texte court)</label>
                <textarea rows={2} className="w-full border rounded-lg px-3 py-2 text-sm" value={content[code]?.sms || ''}
                  onChange={e => setField(code, 'sms', e.target.value)} />
              </div>
            </div>
          ))}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg text-sm text-gray-700 hover:bg-gray-50">Annuler</button>
            <Button onClick={save} variant="primary" size="md" disabled={saving} className="flex-1 font-medium">
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function CommunicationLibrary() {
  const [tpls, setTpls] = useState<Tpl[]>([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<{ ruleType: string, tpl: Tpl | null } | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get<Tpl[]>('/message-templates')
      setTpls(data)
    } catch { /* toast */ } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const select = async (id: string) => {
    try { await apiClient.post(`/message-templates/${id}/select`); toast.success('Modèle sélectionné'); load() }
    catch { /* toast */ }
  }
  const del = async (id: string) => {
    if (!confirm('Supprimer ce modèle ?')) return
    try { await apiClient.delete(`/message-templates/${id}`); toast.success('Modèle supprimé'); load() }
    catch { /* toast */ }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-50 border border-blue-100 text-sm text-blue-800">
        <Globe size={16} className="text-blue-600 shrink-0 mt-0.5" />
        <p>
          Vos <strong>modèles de courrier</strong> (e-mail + SMS), en plusieurs langues. Créez-en autant
          que voulu par type et cochez « Utilisé » pour celui que l'automatisation enverra. Chaque locataire
          reçoit le courrier dans <strong>sa langue</strong> (repli français). L'activation des envois se règle
          dans l'onglet « Automatisation ».
        </p>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-400">Chargement…</div>
      ) : (
        COMM_TYPES.map(type => {
          const list = tpls.filter(t => t.rule_type === type.value)
          return (
            <div key={type.value} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-semibold text-gray-800">{type.label}</p>
                <Button size="sm" variant="secondary" onClick={() => setModal({ ruleType: type.value, tpl: null })}>
                  <Plus size={13} /> Nouveau modèle
                </Button>
              </div>
              {list.length === 0 ? (
                <p className="px-4 py-3 text-sm text-gray-400">Aucun modèle. Le contenu par défaut est utilisé.</p>
              ) : (
                <div className="divide-y divide-gray-50">
                  {list.map(t => (
                    <div key={t.id} className="flex items-center gap-3 px-4 py-2.5">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-800 truncate">{t.name}</span>
                          {t.is_selected && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200">Utilisé</span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.keys(t.content || {}).map(code => (
                            <span key={code} className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{LANG_LABEL[code] || code}</span>
                          ))}
                        </div>
                      </div>
                      {!t.is_selected && (
                        <button onClick={() => select(t.id)} title="Utiliser ce modèle"
                          className="text-xs px-2.5 py-1.5 rounded-lg text-green-700 border border-green-200 hover:bg-green-50">
                          Utiliser
                        </button>
                      )}
                      <button onClick={() => setModal({ ruleType: type.value, tpl: t })} title="Modifier"
                        className="p-1.5 text-gray-500 hover:bg-gray-100 rounded-lg"><Edit2 size={14} /></button>
                      <button onClick={() => del(t.id)} title="Supprimer"
                        className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg"><Trash2 size={14} /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })
      )}

      {modal && (
        <TemplateModal ruleType={modal.ruleType} tpl={modal.tpl}
          onClose={() => setModal(null)} onSaved={load} />
      )}
    </div>
  )
}
