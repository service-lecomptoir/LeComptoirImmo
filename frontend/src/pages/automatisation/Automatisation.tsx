import { useState, useEffect } from 'react'
import { apiClient } from '@/api/client'
import { toast } from '@/store/toast'
import {
  Zap, Trash2, ToggleLeft, ToggleRight,
  Mail, MessageSquare, Bell, Calendar,
  CheckCircle, Clock, AlertTriangle, Users, RefreshCw, Play,
} from 'lucide-react'
import NotificationsSettings from '@/pages/settings/NotificationsSettings'
import CommunicationLibrary from './CommunicationLibrary'
import EmailThemePicker from './EmailThemePicker'

const RULE_TYPES = [
  { value: 'avis_echeance', label: "Avis d'échéance", icon: Calendar, color: 'blue' },
  { value: 'quittance', label: 'Quittance', icon: CheckCircle, color: 'green' },
  { value: 'rappel_impaye', label: 'Rappel impayé', icon: AlertTriangle, color: 'red' },
  { value: 'relance_1', label: 'Relance 1', icon: Bell, color: 'orange' },
  { value: 'relance_2', label: 'Relance 2 (mise en demeure)', icon: Bell, color: 'red' },
  { value: 'revision_loyer', label: 'Révision du loyer', icon: RefreshCw, color: 'blue' },
  { value: 'revision_charges', label: 'Révision des charges', icon: RefreshCw, color: 'orange' },
  { value: 'taxe_om', label: "Taxe d'ordures ménagères", icon: Trash2, color: 'gray' },
  { value: 'rapport_mensuel', label: 'Rapport mensuel de gestion', icon: Clock, color: 'purple' },
  { value: 'communication_groupee', label: 'Communication groupée', icon: Users, color: 'purple' },
]

interface Rule {
  id: string
  name: string
  rule_type: string
  trigger_days: number
  run_hour?: number
  run_minute?: number
  last_run_at?: string | null
  auto_generate?: boolean
  auto_deposit?: boolean
  send_email?: boolean
  send_sms?: boolean
  channel: string
  subject?: string
  body_template?: string
  is_active: boolean
  cc_emails?: string | null
  signature?: string | null
}


interface Log {
  id: string
  channel: string
  recipient?: string
  subject?: string
  status: string
  sent_at: string
}


// ── Onglet Planificateur : calendrier des automatisations ────────────────────
// Vue consolidée de QUAND chaque document/message part, éditable au même endroit
// (le délai est stocké sur la règle). Les types événementiels (quittance,
// révisions, taxe) ne se planifient pas : ils partent au moment de l'action.
const PLAN_EVENT_LABELS: Record<string, string> = {
  quittance: "Dès qu'un mois est intégralement payé",
  revision_loyer: "Dès qu'une révision du loyer est déclarée",
  revision_charges: "Dès qu'une révision des charges est déclarée",
  taxe_om: "Dès qu'une taxe d'ordures ménagères est déclarée",
}
const PLAN_ORDER = ['avis_echeance', 'quittance', 'rappel_impaye', 'relance_1',
  'relance_2', 'revision_loyer', 'revision_charges', 'taxe_om', 'rapport_mensuel']

function planKind(t: string): 'before' | 'after' | 'day' | 'event' | 'hide' {
  if (t === 'avis_echeance') return 'before'
  if (['rappel_impaye', 'relance_1', 'relance_2'].includes(t)) return 'after'
  if (t === 'rapport_mensuel') return 'day'
  if (t === 'communication_groupee') return 'hide'
  return 'event'
}

const pad2 = (n: number) => String(n).padStart(2, '0')

// Petit interrupteur de cellule (une option d'automatisation), sauvegarde immédiate.
function CellToggle({ on, disabled, busy, onToggle }: {
  on: boolean, disabled?: boolean, busy?: boolean, onToggle: () => void
}) {
  if (disabled) return <span className="text-sm text-gray-300">—</span>
  return (
    <button type="button" onClick={onToggle} disabled={busy}
      className="inline-flex disabled:opacity-50">
      {on ? <ToggleRight size={24} className="text-green-600" />
          : <ToggleLeft size={24} className="text-gray-300" />}
    </button>
  )
}

function PlanningRow({ rule, onSaved }: { rule: Rule, onSaved: () => void }) {
  const info = RULE_TYPES.find(t => t.value === rule.rule_type)
  const Icon = info?.icon || Clock
  const kind = planKind(rule.rule_type)
  const base = Math.abs(rule.trigger_days || 0)
  const baseHour = rule.run_hour ?? 8
  const baseMin = rule.run_minute ?? 0
  const [val, setVal] = useState(base)
  const [hour, setHour] = useState(baseHour)
  const [minute, setMinute] = useState(baseMin)
  const [busy, setBusy] = useState(false)
  const scheduled = kind !== 'event'  // avis / rappel / relance / rapport
  const isRapport = rule.rule_type === 'rapport_mensuel'  // gestionnaire only (pas de dépôt/SMS)
  const dirty = scheduled && (val !== base || hour !== baseHour || minute !== baseMin)

  const patch = async (body: Record<string, any>) => {
    setBusy(true)
    try {
      await apiClient.patch(`/automation/rules/${rule.id}`, body)
      onSaved()
    } catch { /* toast via intercepteur */ } finally { setBusy(false) }
  }
  const saveTiming = () => {
    if (!dirty) return
    const td = kind === 'day' ? Math.min(28, Math.max(1, val)) : Math.max(0, val)
    patch({ trigger_days: td, run_hour: Math.min(23, Math.max(0, hour)), run_minute: Math.min(59, Math.max(0, minute)) })
  }

  const runNow = async () => {
    setBusy(true)
    try {
      const { data } = await apiClient.post(`/automation/rules/${rule.id}/run-now`)
      toast.success(data?.message || `Exécution lancée (${data?.count ?? 0})`)
      onSaved()
    } catch { /* toast via intercepteur */ } finally { setBusy(false) }
  }

  const triggerText = kind === 'event' ? PLAN_EVENT_LABELS[rule.rule_type]
    : kind === 'before' ? "avant l'échéance"
    : kind === 'after' ? "après l'échéance"
    : 'du mois'
  const lastRun = rule.last_run_at
    ? new Date(rule.last_run_at).toLocaleString('fr-FR',
        { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'Jamais'

  const td = 'px-3 py-3 align-middle text-center'
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className={td}>
        <div className="flex items-center justify-center gap-2">
          <Icon size={15} className="text-gray-400 shrink-0" />
          <span className="text-sm font-medium text-gray-800">{info?.label || rule.rule_type}</span>
        </div>
      </td>
      <td className={td}>
        {scheduled ? (
          <div className="flex items-center justify-center gap-1.5">
            {kind === 'day' && <span className="text-xs text-gray-500">Le</span>}
            <input type="number" min={kind === 'day' ? 1 : 0} max={kind === 'day' ? 28 : 60}
              value={val} onChange={e => setVal(parseInt(e.target.value) || 0)} onBlur={saveTiming}
              className="w-14 border rounded-lg px-2 py-1.5 text-sm text-center" />
            <span className="text-xs text-gray-500 whitespace-nowrap">{triggerText}</span>
          </div>
        ) : (
          <span className="text-sm text-gray-500">{triggerText}</span>
        )}
      </td>
      <td className={td}>
        {scheduled ? (
          <input type="time" value={`${pad2(hour)}:${pad2(minute)}`}
            onChange={e => { const [h, m] = e.target.value.split(':'); setHour(parseInt(h) || 0); setMinute(parseInt(m) || 0) }}
            onBlur={saveTiming}
            className="border rounded-lg px-2 py-1.5 text-sm text-center" />
        ) : (
          <span className="text-sm text-gray-400">—</span>
        )}
      </td>
      <td className={td}><CellToggle on={rule.auto_generate !== false} busy={busy} onToggle={() => patch({ auto_generate: !(rule.auto_generate !== false) })} /></td>
      <td className={td}><CellToggle on={rule.auto_deposit !== false} disabled={isRapport} busy={busy} onToggle={() => patch({ auto_deposit: !(rule.auto_deposit !== false) })} /></td>
      <td className={td}><CellToggle on={rule.send_email !== false} busy={busy} onToggle={() => patch({ send_email: !(rule.send_email !== false) })} /></td>
      <td className={td}><CellToggle on={!!rule.send_sms} disabled={isRapport} busy={busy} onToggle={() => patch({ send_sms: !rule.send_sms })} /></td>
      <td className={`${td} text-sm text-gray-600 whitespace-nowrap`}>{lastRun}</td>
      <td className={td}>
        {scheduled
          ? <button type="button" onClick={runNow} disabled={busy}
              title="Démarrer maintenant"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:opacity-50">
              <Play size={13} className={busy ? 'animate-pulse' : ''} fill="currentColor" />
              {busy ? '…' : 'Start'}
            </button>
          : <span className="text-sm text-gray-400">—</span>}
      </td>
    </tr>
  )
}

function AutomationPlanning({ rules, onSaved }: { rules: Rule[], onSaved: () => void }) {
  const items = rules
    .filter(r => planKind(r.rule_type) !== 'hide')
    .sort((a, b) => PLAN_ORDER.indexOf(a.rule_type) - PLAN_ORDER.indexOf(b.rule_type))
  const th = 'px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide'
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-2">
        <Calendar size={18} className="text-blue-600" />
        <h2 className="text-base font-bold text-gray-900">Tâche programmée</h2>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Pour chaque document, activez ou non : <strong>Générer</strong> (automatiser),
        <strong> Déposer</strong> (sur le compte du locataire), <strong>E-mail</strong> (avec le
        document en pièce jointe) et <strong>SMS</strong>. Réglez le délai et l'heure (hh:mm) pour
        les types planifiés ; les types « à l'événement » se déclenchent à l'action (paiement,
        déclaration). Rien ne part sans votre accord. Le contenu des courriers se règle dans l'onglet
        « Communication ».
      </p>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400">Aucune automatisation configurée.</p>
      ) : (
        <div>
          <table className="w-full table-auto text-sm">
            <thead className="bg-gray-50 border-y border-gray-100">
              <tr>
                <th className={th}>Document</th>
                <th className={th}>Déclenchement</th>
                <th className={th}>Heure</th>
                <th className={th}>Générer</th>
                <th className={th}>Déposer</th>
                <th className={th}>E-mail</th>
                <th className={th}>SMS</th>
                <th className={th}>Dernière exécution</th>
                <th className={th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map(r => (
                <PlanningRow key={r.id} rule={r} onSaved={onSaved} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function Automatisation() {
  const [rules, setRules] = useState<Rule[]>([])
  const [logs, setLogs] = useState<Log[]>([])
  const [activeTab, setActiveTab] = useState<'rules' | 'logs' | 'scheduler' | 'canaux' | 'apparence'>('rules')

  const load = async () => {
    try {
      const [rulesRes, logsRes] = await Promise.all([
        apiClient.get('/automation/rules'),
        apiClient.get('/automation/logs'),
      ])
      setRules(rulesRes.data)
      setLogs(logsRes.data)
    } catch { }
  }

  useEffect(() => { load() }, [])

  const deleteLog = async (id: string) => {
    if (!confirm('Supprimer cette ligne de l\'historique ?')) return
    try {
      await apiClient.delete(`/automation/logs/${id}`)
      toast.success('Ligne supprimée.')
      load()
    } catch {
      // erreur affichée par l'intercepteur (toast)
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Communication et automatisation</h1>
          <p className="text-sm text-gray-500 mt-1">Modèles de courrier et automatisation des envois</p>
        </div>
      </div>

      {/* Bandeau : les tâches programmées pilotent les envois automatiques */}
      <div className="mb-6 flex items-start gap-2 p-3 rounded-lg bg-blue-50 border border-blue-100 text-sm text-blue-800">
        <Zap size={16} className="text-blue-600 shrink-0 mt-0.5" />
        <p>
          Les <strong>tâches programmées</strong> pilotent tous les envois automatiques aux locataires (e-mail / SMS).
          Les avis partent selon le délai <em>avant</em> l'échéance ; les rappels et relances, selon le délai
          <em> après</em> l'échéance tant que le loyer reste impayé ; la quittance dès qu'un mois est soldé.
          Le contrôle est automatique ; le bouton « Start » force un passage immédiat.
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
              <p className="text-xs text-gray-500">Tâches actives</p>
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
              <p className="text-xs text-gray-500">Tâches totales</p>
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
          { key: 'rules', label: 'Communication' },
          { key: 'logs', label: 'Historique des envois' },
          { key: 'scheduler', label: 'Automatisation' },
          { key: 'apparence', label: 'Apparence des e-mails' },
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

      {activeTab === 'rules' && <CommunicationLibrary />}

      {activeTab === 'apparence' && <EmailThemePicker />}

      {activeTab === 'logs' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          {logs.length === 0 ? (
            <div className="text-center py-12 text-gray-400">Aucun envoi enregistré</div>
          ) : (
            <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">Date</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">Canal</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">Destinataire</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">Objet</th>
                  <th className="text-center px-4 py-3 text-xs font-medium text-gray-500">Statut</th>
                  <th className="px-4 py-3 text-xs font-medium text-gray-500 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-500 text-center">
                      {new Date(log.sent_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="flex items-center gap-1 text-xs">
                        {log.channel === 'email' ? <Mail size={12} /> : <MessageSquare size={12} />}
                        {log.channel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600 text-center">{log.recipient}</td>
                    <td className="px-4 py-3 text-xs text-gray-600 max-w-xs truncate text-center">{log.subject}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${
                        log.status === 'sent' ? 'bg-green-100 text-green-700' :
                        log.status === 'simulated' ? 'bg-blue-100 text-blue-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {log.status === 'sent' ? <CheckCircle size={10} /> : <Clock size={10} />}
                        {log.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button onClick={() => deleteLog(log.id)} title="Supprimer cette ligne"
                        className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg">
                        <Trash2 size={14} />
                      </button>
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
        <div className="space-y-6">
          {/* Calendrier : génération + dépôt de chaque document, heure & exécution */}
          <AutomationPlanning rules={rules} onSaved={load} />
        </div>
      )}

      {/* Onglet Canaux & tests (état e-mail/SMS, test d'envoi, CC gestionnaire) ── */}
      {activeTab === 'canaux' && (
        <NotificationsSettings embedded />
      )}
    </div>
  )
}
