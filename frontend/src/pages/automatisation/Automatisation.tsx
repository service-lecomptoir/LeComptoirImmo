import { useState, useEffect } from 'react'
import { getErrorMessage } from '@/utils/errors'
import { apiClient } from '@/api/client'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'
import {
  Zap, Plus, Trash2, Edit2, ToggleLeft, ToggleRight,
  Mail, MessageSquare, Bell, Calendar, Send,
  CheckCircle, Clock, AlertTriangle, Users, Settings, RefreshCw,
} from 'lucide-react'
import { schedulerApi, avisEcheancesApi } from '@/api/avis_echeances'
import NotificationsSettings from '@/pages/settings/NotificationsSettings'

const RULE_TYPES = [
  { value: 'avis_echeance', label: "Avis d'échéance", icon: Calendar, color: 'blue' },
  { value: 'quittance', label: 'Quittance', icon: CheckCircle, color: 'green' },
  { value: 'rappel_impaye', label: 'Rappel impayé', icon: AlertTriangle, color: 'red' },
  { value: 'relance_1', label: 'Relance 1', icon: Bell, color: 'orange' },
  { value: 'relance_2', label: 'Relance 2 (mise en demeure)', icon: Bell, color: 'red' },
  { value: 'communication_groupee', label: 'Communication groupée', icon: Users, color: 'purple' },
]

const CHANNELS = [
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'sms', label: 'SMS', icon: MessageSquare },
  { value: 'email_sms', label: 'Email + SMS', icon: Mail },
]

const RULE_COLORS: Record<string, string> = {
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
  green: 'bg-green-50 text-green-700 border-green-200',
  red: 'bg-red-50 text-red-700 border-red-200',
  orange: 'bg-orange-50 text-orange-700 border-orange-200',
  purple: 'bg-purple-50 text-purple-700 border-purple-200',
}

interface Rule {
  id: string
  name: string
  rule_type: string
  trigger_days: number
  channel: string
  subject?: string
  body_template?: string
  is_active: boolean
  cc_emails?: string | null
}

interface Log {
  id: string
  channel: string
  recipient?: string
  subject?: string
  status: string
  sent_at: string
}

function RuleModal({ rule, onClose, onSaved }: { rule?: Rule | null, onClose: () => void, onSaved: () => void }) {
  const [form, setForm] = useState({
    name: rule?.name || '',
    rule_type: rule?.rule_type || 'avis_echeance',
    trigger_days: rule?.trigger_days ?? 5,
    channel: rule?.channel || 'email',
    subject: rule?.subject || '',
    body_template: rule?.body_template || '',
    is_active: rule?.is_active ?? true,
    cc_emails: rule?.cc_emails || '',
  })
  const [saving, setSaving] = useState(false)
  const myEmail = useAuthStore(s => s.user?.email) || ''

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (rule?.id) {
        await apiClient.patch(`/automation/rules/${rule.id}`, form)
      } else {
        await apiClient.post('/automation/rules', form)
      }
      onSaved()
      onClose()
    } catch {
      // erreur affichée par l'intercepteur (toast) — la modale reste ouverte
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">
            {rule ? 'Modifier la règle' : 'Nouvelle règle d\'automatisation'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom de la règle *</label>
            <input required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })} />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type d'automatisation</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {RULE_TYPES.map(t => {
                const Icon = t.icon
                return (
                  <button key={t.value} type="button"
                    onClick={() => setForm({ ...form, rule_type: t.value })}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs transition-all ${
                      form.rule_type === t.value
                        ? `${RULE_COLORS[t.color]} font-medium`
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon size={14} />
                    {t.label}
                  </button>
                )
              })}
            </div>
          </div>

          {(() => {
            const isAvis = form.rule_type === 'avis_echeance'
            const isReminder = ['rappel_impaye', 'relance_1', 'relance_2'].includes(form.rule_type)
            const isEvent = form.rule_type === 'quittance'
            const isManual = form.rule_type === 'communication_groupee'
            if (isEvent) return (
              <p className="text-sm text-gray-500">
                La quittance est envoyée automatiquement dès qu'un mois est intégralement réglé (aucun délai à régler).
              </p>
            )
            if (isManual) return (
              <p className="text-sm text-gray-500">Communication ponctuelle, déclenchée manuellement (aucun délai).</p>
            )
            const d = Math.abs(form.trigger_days || 0)
            const dir = isAvis ? 'avant' : 'après'
            return (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {isAvis ? "Délai (jours avant l'échéance)" : "Délai (jours après l'échéance)"}
                </label>
                <div className="flex items-center gap-3">
                  <input type="number" min={0} max={60}
                    className="w-24 border rounded-lg px-3 py-2 text-sm text-center"
                    value={d}
                    onChange={e => setForm({ ...form, trigger_days: Math.abs(parseInt(e.target.value) || 0) })} />
                  <span className="text-sm text-gray-500">
                    {d === 0 ? "Le jour de l'échéance" : `${d} jour${d > 1 ? 's' : ''} ${dir} l'échéance`}
                  </span>
                </div>
                {isReminder && (
                  <p className="text-xs text-gray-400 mt-1">
                    Envoyé tant que le loyer reste impayé après ce délai.
                  </p>
                )}
              </div>
            )
          })()}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Canal d'envoi</label>
            <div className="flex gap-2">
              {CHANNELS.map(ch => {
                const Icon = ch.icon
                return (
                  <button key={ch.value} type="button"
                    onClick={() => setForm({ ...form, channel: ch.value })}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all ${
                      form.channel === ch.value
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Icon size={14} />
                    {ch.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Objet du message</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="ex: Avis d'échéance - {{month}}"
              value={form.subject}
              onChange={e => setForm({ ...form, subject: e.target.value })} />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Corps du message</label>
            <p className="text-xs text-gray-400 mb-1">Variables disponibles : {'{{'} tenant_name {'}}'}, {'{{'} amount {'}}'}, {'{{'} due_date {'}}'}, {'{{'} month {'}}'}</p>
            <textarea rows={5} className="w-full border rounded-lg px-3 py-2 text-sm font-mono text-xs"
              value={form.body_template}
              onChange={e => setForm({ ...form, body_template: e.target.value })} />
          </div>

          {(form.channel === 'email' || form.channel === 'email_sms') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Gestionnaire en copie (CC)</label>
              <input type="email" list="cc-suggestions" inputMode="email" autoComplete="email"
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="adresse e-mail à mettre en copie"
                value={form.cc_emails}
                onChange={e => setForm({ ...form, cc_emails: e.target.value })} />
              <datalist id="cc-suggestions">
                {myEmail && <option value={myEmail} />}
              </datalist>
              <div className="flex items-center gap-2 mt-1.5">
                {myEmail && form.cc_emails.trim() !== myEmail && (
                  <button type="button" onClick={() => setForm({ ...form, cc_emails: myEmail })}
                    className="text-xs text-blue-600 hover:underline">
                    + Me mettre en copie ({myEmail})
                  </button>
                )}
                <p className="text-xs text-gray-400">Laisser vide pour n'envoyer qu'au locataire. Plusieurs adresses : séparées par des virgules.</p>
              </div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <input type="checkbox" id="active" checked={form.is_active}
              onChange={e => setForm({ ...form, is_active: e.target.checked })} />
            <label htmlFor="active" className="text-sm text-gray-700">Règle active</label>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg text-sm text-gray-700 hover:bg-gray-50">
              Annuler
            </button>
            <button type="submit" disabled={saving}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Sauvegarde...' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function GroupCommunicationModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({
    subject: '',
    body: '',
    channel: 'email',
    all_tenants: true,
  })
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    setSending(true)
    try {
      const r = await apiClient.post('/automation/send-group', form)
      setResult(r.data)
    } catch {
      // erreur affichée par l'intercepteur (toast)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
        <div className="border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Communication groupée</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
        </div>
        {result ? (
          <div className="p-6 text-center">
            <CheckCircle size={48} className="mx-auto text-green-500 mb-3" />
            <p className="text-lg font-semibold text-gray-900">{result.message}</p>
            <p className="text-sm text-gray-500 mt-1">{result.sent_count} / {result.total_targets} destinataire{result.total_targets > 1 ? 's' : ''}</p>
            <button onClick={onClose}
              className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              Fermer
            </button>
          </div>
        ) : (
          <form onSubmit={handleSend} className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Canal</label>
              <div className="flex gap-2">
                {CHANNELS.map(ch => (
                  <button key={ch.value} type="button"
                    onClick={() => setForm({ ...form, channel: ch.value })}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
                      form.channel === ch.value ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 text-gray-600'
                    }`}
                  >
                    {ch.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Objet *</label>
              <input required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.subject}
                onChange={e => setForm({ ...form, subject: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Message *</label>
              <textarea required rows={6} className="w-full border rounded-lg px-3 py-2 text-sm" value={form.body}
                onChange={e => setForm({ ...form, body: e.target.value })} />
            </div>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-xs text-yellow-800">
              ⚠️ Ce message sera envoyé à tous les locataires actifs. Vérifiez le contenu avant d'envoyer.
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={onClose}
                className="flex-1 px-4 py-2 border rounded-lg text-sm text-gray-700 hover:bg-gray-50">
                Annuler
              </button>
              <button type="submit" disabled={sending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                <Send size={14} />
                {sending ? 'Envoi...' : 'Envoyer'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default function Automatisation() {
  const [rules, setRules] = useState<Rule[]>([])
  const [logs, setLogs] = useState<Log[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'rules' | 'logs' | 'scheduler' | 'canaux'>('rules')
  const [showRuleModal, setShowRuleModal] = useState(false)
  const [showGroupModal, setShowGroupModal] = useState(false)
  const [editRule, setEditRule] = useState<Rule | null>(null)

  // ── Scheduler state ──────────────────────────────────────────────────────────
  const [schedulerDay, setSchedulerDay] = useState(1)
  const [schedulerHour, setSchedulerHour] = useState(7)
  const [schedulerMinute, setSchedulerMinute] = useState(30)
  const [schedulerNextRun, setSchedulerNextRun] = useState<string | null>(null)
  const [schedulerSaving, setSchedulerSaving] = useState(false)
  const [schedulerMsg, setSchedulerMsg] = useState('')
  const [generatingBulk, setGeneratingBulk] = useState(false)
  const [bulkMsg, setBulkMsg] = useState('')

  const loadScheduler = async () => {
    try {
      const { data } = await schedulerApi.getConfig()
      setSchedulerDay(data.day)
      setSchedulerHour(data.hour)
      setSchedulerMinute(data.minute)
      setSchedulerNextRun(data.next_run)
    } catch {}
  }

  const saveScheduler = async () => {
    setSchedulerSaving(true); setSchedulerMsg('')
    try {
      const { data } = await schedulerApi.updateConfig({ day: schedulerDay, hour: schedulerHour, minute: schedulerMinute })
      setSchedulerNextRun(data.next_run)
      setSchedulerMsg('Configuration enregistrée et scheduler mis à jour.')
      setTimeout(() => setSchedulerMsg(''), 4000)
    } catch (e: any) {
      setSchedulerMsg('Erreur : ' + (getErrorMessage(e, 'inconnue')))
    } finally {
      setSchedulerSaving(false)
    }
  }

  const triggerBulkNow = async () => {
    const now = new Date()
    setGeneratingBulk(true); setBulkMsg('')
    try {
      const { data } = await avisEcheancesApi.generateMonthly({
        period_year: now.getFullYear(),
        period_month: now.getMonth() + 1,
      })
      setBulkMsg(data.message)
      setTimeout(() => setBulkMsg(''), 5000)
    } catch (e: any) {
      setBulkMsg('Erreur : ' + (getErrorMessage(e, 'inconnue')))
    } finally {
      setGeneratingBulk(false)
    }
  }

  const load = async () => {
    setLoading(true)
    try {
      const [rulesRes, logsRes] = await Promise.all([
        apiClient.get('/automation/rules'),
        apiClient.get('/automation/logs'),
      ])
      setRules(rulesRes.data)
      setLogs(logsRes.data)
    } catch { }
    setLoading(false)
  }

  useEffect(() => { load(); loadScheduler() }, [])

  const toggleRule = async (id: string) => {
    try {
      await apiClient.post(`/automation/rules/${id}/toggle`)
      load()
    } catch {
      // erreur affichée par l'intercepteur (toast)
    }
  }

  const deleteRule = async (id: string) => {
    if (!confirm('Supprimer cette règle ?')) return
    try {
      await apiClient.delete(`/automation/rules/${id}`)
      load()
    } catch {
      // erreur affichée par l'intercepteur (toast)
    }
  }

  const getRuleInfo = (type: string) => RULE_TYPES.find(t => t.value === type)

  const [running, setRunning] = useState(false)
  const runNow = async () => {
    setRunning(true)
    try {
      const { data } = await apiClient.post('/automation/run')
      const n = data?.sent ?? 0
      toast.success(n > 0
        ? `${n} envoi(s) déclenché(s) par vos règles.`
        : 'Aucun envoi à effectuer pour le moment (rien d\'éligible).')
      load()
    } catch {
      // toast via intercepteur
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Règles d'automatisation</h1>
          <p className="text-sm text-gray-500 mt-1">Avis d'échéance, quittances, rappels, communications</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runNow} disabled={running}
            className="flex items-center gap-2 px-4 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw size={16} className={running ? 'animate-spin' : ''} />
            {running ? 'Exécution…' : 'Exécuter maintenant'}
          </button>
          <button
            onClick={() => setShowGroupModal(true)}
            className="flex items-center gap-2 px-4 py-2 border border-blue-200 text-blue-600 rounded-lg text-sm font-medium hover:bg-blue-50"
          >
            <Send size={16} />
            Communication groupée
          </button>
          <button
            onClick={() => { setEditRule(null); setShowRuleModal(true) }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            <Plus size={16} />
            Nouvelle règle
          </button>
        </div>
      </div>

      {/* Bandeau : les règles pilotent réellement les envois */}
      <div className="mb-6 flex items-start gap-2 p-3 rounded-lg bg-blue-50 border border-blue-100 text-sm text-blue-800">
        <Zap size={16} className="text-blue-600 shrink-0 mt-0.5" />
        <p>
          Ces règles pilotent <strong>tous les envois automatiques</strong> aux locataires (e-mail / SMS).
          Les avis sont envoyés selon le délai <em>avant</em> l'échéance ; les rappels et relances, selon le délai
          <em> après</em> l'échéance tant que le loyer reste impayé ; la quittance part dès qu'un mois est soldé.
          Le contrôle quotidien est automatique ; « Exécuter maintenant » force un passage immédiat.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
              <Zap size={20} className="text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{rules.filter(r => r.is_active).length}</p>
              <p className="text-xs text-gray-500">Règles actives</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
              <Clock size={20} className="text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{rules.length}</p>
              <p className="text-xs text-gray-500">Règles totales</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-xl flex items-center justify-center">
              <Mail size={20} className="text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{logs.length}</p>
              <p className="text-xs text-gray-500">Messages envoyés</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b mb-6">
        {([
          { key: 'rules', label: "Règles d'automatisation" },
          { key: 'logs', label: 'Historique des envois' },
          { key: 'scheduler', label: 'Planificateur' },
          { key: 'canaux', label: 'Canaux & tests' },
        ] as const).map(tab => (
          <button key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'rules' && (
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-8 text-gray-400">Chargement…</div>
          ) : rules.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border">
              <Zap size={48} className="mx-auto text-gray-300 mb-3" />
              <p className="text-gray-500 mb-2">Aucune règle d'automatisation configurée</p>
              <button
                onClick={() => { setEditRule(null); setShowRuleModal(true) }}
                className="text-blue-600 text-sm hover:underline"
              >
                Créer votre première règle
              </button>
            </div>
          ) : (
            rules.map(rule => {
              const info = getRuleInfo(rule.rule_type)
              const Icon = info?.icon || Bell
              return (
                <div key={rule.id}
                  className={`bg-white rounded-xl border p-4 flex items-center gap-4 ${!rule.is_active ? 'opacity-60' : ''}`}
                >
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    info ? RULE_COLORS[info.color].replace('border-', '').replace('text-', 'text-') : 'bg-gray-100'
                  }`}>
                    <Icon size={18} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-gray-900 text-sm">{rule.name}</p>
                      {!rule.is_active && (
                        <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Inactive</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {info?.label} · {
                        rule.trigger_days > 0 ? `${rule.trigger_days}j avant` :
                        rule.trigger_days < 0 ? `${Math.abs(rule.trigger_days)}j après` : 'Le jour J'
                      } · {CHANNELS.find(c => c.value === rule.channel)?.label}
                    </p>
                    {rule.subject && (
                      <p className="text-xs text-gray-400 mt-0.5 truncate">"{rule.subject}"</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <button onClick={() => toggleRule(rule.id)} title={rule.is_active ? 'Désactiver' : 'Activer'}>
                      {rule.is_active
                        ? <ToggleRight size={24} className="text-green-500" />
                        : <ToggleLeft size={24} className="text-gray-400" />
                      }
                    </button>
                    <button onClick={() => { setEditRule(rule); setShowRuleModal(true) }}
                      className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg">
                      <Edit2 size={14} />
                    </button>
                    <button onClick={() => deleteRule(rule.id)}
                      className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          {logs.length === 0 ? (
            <div className="text-center py-12 text-gray-400">Aucun envoi enregistré</div>
          ) : (
            <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Date</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Canal</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Destinataire</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Objet</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Statut</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(log.sent_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-xs">
                        {log.channel === 'email' ? <Mail size={12} /> : <MessageSquare size={12} />}
                        {log.channel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">{log.recipient}</td>
                    <td className="px-4 py-3 text-xs text-gray-600 max-w-xs truncate">{log.subject}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                        log.status === 'sent' ? 'bg-green-100 text-green-700' :
                        log.status === 'simulated' ? 'bg-blue-100 text-blue-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {log.status === 'sent' ? <CheckCircle size={10} /> : <Clock size={10} />}
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </div>
      )}

      {/* Onglet Planificateur ─────────────────────────────────────────── */}
      {activeTab === 'scheduler' && (
        <div className="max-w-2xl space-y-6">

          {/* Config scheduler */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-5">
              <Settings size={18} className="text-blue-600" />
              <h2 className="text-base font-bold text-gray-900">Planification automatique des avis</h2>
            </div>
            <p className="text-sm text-gray-500 mb-5">
              Le planificateur génère automatiquement les avis d'échéance pour tous les baux actifs chaque mois
              à l'heure configurée. Seuls les baux sans avis existant pour la période sont traités.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Jour du mois</label>
                <select
                  value={schedulerDay}
                  onChange={e => setSchedulerDay(Number(e.target.value))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Array.from({ length: 28 }, (_, i) => i + 1).map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-400 mt-1">1 à 28 (sûr pour tous les mois)</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Heure</label>
                <select
                  value={schedulerHour}
                  onChange={e => setSchedulerHour(Number(e.target.value))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Array.from({ length: 24 }, (_, i) => i).map(h => (
                    <option key={h} value={h}>{String(h).padStart(2, '0')}h</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1.5">Minute</label>
                <select
                  value={schedulerMinute}
                  onChange={e => setSchedulerMinute(Number(e.target.value))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {[0, 15, 30, 45].map(m => (
                    <option key={m} value={m}>{String(m).padStart(2, '0')}</option>
                  ))}
                </select>
              </div>
            </div>

            {schedulerNextRun && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-4 flex items-center gap-2">
                <Clock size={14} className="text-blue-500 shrink-0" />
                <span className="text-sm text-blue-700">
                  Prochaine exécution :{' '}
                  <span className="font-semibold">
                    {new Date(schedulerNextRun).toLocaleDateString('fr-FR', {
                      weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })}
                  </span>
                </span>
              </div>
            )}

            {schedulerMsg && (
              <div className={`mb-4 px-4 py-2 rounded-lg text-sm border ${
                schedulerMsg.startsWith('Erreur')
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-green-50 text-green-700 border-green-200'
              }`}>
                {schedulerMsg}
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={saveScheduler}
                disabled={schedulerSaving}
                className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                <Settings size={14} />
                {schedulerSaving ? 'Enregistrement…' : 'Enregistrer la planification'}
              </button>
            </div>
          </div>

          {/* Déclenchement manuel */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-3">
              <RefreshCw size={18} className="text-purple-600" />
              <h2 className="text-base font-bold text-gray-900">Lancer maintenant</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Génère immédiatement les avis d'échéance pour le mois en cours (
              {new Date().toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}).
              Les baux ayant déjà un avis pour ce mois sont ignorés.
            </p>
            {bulkMsg && (
              <div className={`mb-4 px-4 py-2 rounded-lg text-sm border ${
                bulkMsg.startsWith('Erreur')
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-green-50 text-green-700 border-green-200'
              }`}>
                {bulkMsg}
              </div>
            )}
            <button
              onClick={triggerBulkNow}
              disabled={generatingBulk}
              className="flex items-center gap-2 px-5 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
            >
              <RefreshCw size={14} className={generatingBulk ? 'animate-spin' : ''} />
              {generatingBulk ? 'Génération en cours…' : 'Générer les avis du mois'}
            </button>
          </div>
        </div>
      )}

      {/* Onglet Canaux & tests (état e-mail/SMS, test d'envoi, CC gestionnaire) ── */}
      {activeTab === 'canaux' && (
        <NotificationsSettings embedded />
      )}

      {showRuleModal && (
        <RuleModal rule={editRule} onClose={() => setShowRuleModal(false)} onSaved={load} />
      )}
      {showGroupModal && (
        <GroupCommunicationModal onClose={() => { setShowGroupModal(false); load() }} />
      )}
    </div>
  )
}
