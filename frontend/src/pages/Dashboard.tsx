import { useState, useEffect } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'
import {
  Building2, TrendingUp, AlertTriangle, Home,
  CreditCard, CheckCircle, ArrowUpRight, ArrowDownRight,
  Activity, Euro, RefreshCw, Wrench, KeyRound, FileText
} from 'lucide-react'
import { getDayMoment, formatLongDate } from '@/lib/dayMoment'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/api/client'
import { getErrorMessage } from '@/utils/errors'
import { useAuthStore } from '@/store/authStore'

const MONTH_LABELS: Record<string, string> = {
  '01': 'Jan', '02': 'Fév', '03': 'Mar', '04': 'Avr',
  '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Aoû',
  '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Déc',
}

function fmt(n: number) {
  return new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n)
}

function fmtEur(n: number) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n)
}

// Mois courant en clair, ex. « juin 2026 » (les stats financières/occupation
// portent toujours sur le mois en cours).
function moisCourant() {
  return new Date().toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })
}

// Répartition des contrats actifs par type, ex. « 3 nus · 5 meublés ».
const LEASE_TYPE_SHORT: Record<string, string> = {
  vide: 'nu', meuble: 'meublé', mobilite: 'mobilité', commercial: 'commercial',
}
function repartitionContrats(byType: Record<string, number>): string {
  const order = ['vide', 'meuble', 'mobilite', 'commercial']
  const parts: string[] = []
  for (const k of order) {
    const n = byType?.[k]
    if (n) parts.push(`${n} ${LEASE_TYPE_SHORT[k]}${n > 1 ? 's' : ''}`)
  }
  for (const k of Object.keys(byType || {})) {
    if (!order.includes(k) && byType[k]) parts.push(`${byType[k]} ${k}`)
  }
  return parts.length ? parts.join(' · ') : 'Aucun'
}

interface Stats {
  occupancy: { total_units: number; occupied_units: number; vacant_units: number; occupancy_rate: number }
  financial: { total_rent_expected: number; total_rent_received: number; total_outstanding: number; collection_rate: number; total_deposits: number }
  monthly_revenues: Array<{ month: string; expected: number; received: number; outstanding: number }>
  top_properties: Array<{ property_id: string; property_name: string; units_count: number; occupied_count: number; monthly_revenue: number; outstanding: number }>
  by_owner?: Array<{ owner_name: string; properties_count: number; occupied_count: number; monthly_revenue: number; outstanding: number }>
  alerts: { leases_expiring_30d: number; leases_expiring_90d: number; overdue_payments: number; overdue_amount: number; tenants_no_insurance: number }
  total_tenants: number
  total_properties: number
  total_leases_active: number
  total_leases_future: number
  active_leases_by_type: Record<string, number>
  upcoming_entretiens?: Array<{ id: string; title: string; type: string; status: string; scheduled_date: string; property_label?: string | null; overdue: boolean }>
}

function KPICard({ title, value, sub, icon: Icon, color, trend }: {
  title: string; value: string; sub?: string
  icon: React.ElementType; color: string; trend?: number
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
  }
  return (
    <div className="bg-white rounded-xl border p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colors[color]}`}>
          <Icon size={20} />
        </div>
        {trend !== undefined && (
          <div className={`flex items-center gap-0.5 text-xs font-medium ${trend >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {trend >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm font-medium text-gray-600 mt-0.5">{title}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const isMandataire = useAuthStore(s => s.user?.role === 'gestionnaire')
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    apiClient.get<Stats>('/dashboard/stats')
      .then(r => { setStats(r.data); setError(null) })
      .catch(e => {
        setStats(null)
        setError(e?.response?.status === 403
          ? 'Accès refusé : rôle gestionnaire requis'
          : getErrorMessage(e, 'Erreur : vérifiez que le serveur est démarré'))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full" />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="p-6 text-center text-gray-500">
        <Activity size={48} className="mx-auto mb-3 text-gray-300" />
        <p className="font-medium">Impossible de charger les statistiques</p>
        {error && <p className="text-sm text-red-500 mt-1">{error}</p>}
        <button
          onClick={load}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <RefreshCw size={14} /> Réessayer
        </button>
      </div>
    )
  }

  const monthlyData = stats.monthly_revenues.map(m => ({
    name: MONTH_LABELS[m.month.split('-')[1]] || m.month,
    Encaissé: m.received,
    Attendu: m.expected,
    Impayé: m.outstanding,
  }))

  const occupancyData = [
    { name: 'Occupé', value: stats.occupancy.occupied_units },
    { name: 'Vacant', value: stats.occupancy.vacant_units },
  ]

  const hasAlerts = stats.alerts.leases_expiring_30d > 0 ||
    stats.alerts.overdue_payments > 0 || stats.alerts.leases_expiring_90d > 0

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
          <p className="text-sm text-gray-500 mt-1">Vue d'ensemble de votre portefeuille</p>
        </div>
        {(() => {
          const moment = getDayMoment()
          const { Icon } = moment
          return (
            <div className="flex items-center gap-2.5">
              <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
                style={{ background: moment.bg }} title={moment.label}>
                <Icon size={18} style={{ color: moment.color }} />
              </span>
              <div>
                <p className="text-xs font-medium text-gray-600 leading-tight">{moment.label}</p>
                <p className="text-sm text-gray-500 capitalize">{formatLongDate()}</p>
              </div>
            </div>
          )
        })()}
      </div>

      {/* Alertes */}
      {hasAlerts && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={18} className="text-amber-600" />
            <h3 className="font-semibold text-amber-800">Points d'attention</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {stats.alerts.leases_expiring_30d > 0 && (
              <span className="bg-amber-100 text-amber-800 px-3 py-1 rounded-full text-xs font-medium">
                {stats.alerts.leases_expiring_30d} {stats.alerts.leases_expiring_30d > 1 ? 'baux expirent' : 'bail expire'} dans 30 jours
              </span>
            )}
            {stats.alerts.leases_expiring_90d > 0 && (
              <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-xs font-medium">
                {stats.alerts.leases_expiring_90d} {stats.alerts.leases_expiring_90d > 1 ? 'baux expirent' : 'bail expire'} dans 90 jours
              </span>
            )}
            {stats.alerts.overdue_payments > 0 && (
              <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-xs font-medium">
                {stats.alerts.overdue_payments} paiement{stats.alerts.overdue_payments > 1 ? 's' : ''} en retard : {fmtEur(stats.alerts.overdue_amount)}
              </span>
            )}
          </div>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title={stats.total_properties > 1 ? 'Biens immobiliers' : 'Bien immobilier'} value={fmt(stats.total_properties)}
          sub={`${stats.occupancy.total_units} unité${stats.occupancy.total_units > 1 ? 's' : ''}`} icon={Building2} color="blue" />
        <KPICard title={stats.total_leases_active > 1 ? 'Contrats actifs' : 'Contrat actif'} value={fmt(stats.total_leases_active)}
          sub={repartitionContrats(stats.active_leases_by_type)} icon={FileText} color="green" />
        <KPICard title={`Occupation du parc pour ${moisCourant()}`} value={`${stats.occupancy.occupancy_rate}%`}
          sub={`${stats.occupancy.occupied_units}/${stats.occupancy.total_units} loué${stats.occupancy.occupied_units > 1 ? 's' : ''}`
            + ` · ${stats.occupancy.vacant_units} vacant${stats.occupancy.vacant_units > 1 ? 's' : ''}`
            + (stats.total_leases_future > 0
              ? ` dont ${stats.total_leases_future} à venir`
              : '')}
          icon={Home} color="purple" />
        <KPICard title="Impayés" value={fmtEur(stats.financial.total_outstanding)}
          sub={stats.alerts.overdue_payments > 0
            ? `${stats.alerts.overdue_payments} paiement${stats.alerts.overdue_payments > 1 ? 's' : ''} en retard`
            : 'À jour'} icon={AlertTriangle}
          color={stats.financial.total_outstanding > 0 ? 'red' : 'green'} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title={`Loyers attendus pour ${moisCourant()}`} value={fmtEur(stats.financial.total_rent_expected)}
          icon={Euro} color="blue" />
        <KPICard title={`Loyers encaissés pour ${moisCourant()}`} value={fmtEur(stats.financial.total_rent_received)}
          sub={`Recouvrement : ${stats.financial.collection_rate}%`} icon={CheckCircle} color="green" />
        <KPICard title="Dépôts de garantie" value={fmtEur(stats.financial.total_deposits)}
          sub="Cautions détenues" icon={CreditCard} color="purple" />
        <KPICard title="Taux de recouvrement" value={`${stats.financial.collection_rate}%`}
          icon={TrendingUp}
          color={stats.financial.collection_rate >= 95 ? 'green' : stats.financial.collection_rate >= 80 ? 'orange' : 'red'} />
      </div>

      {/* Graphiques */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Revenus : 12 derniers mois</h2>
            <div className="flex gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1"><span className="w-3 h-2 bg-blue-500 inline-block rounded-sm" /> Encaissé</span>
              <span className="flex items-center gap-1"><span className="w-3 h-2 bg-blue-200 inline-block rounded-sm" /> Attendu</span>
              <span className="flex items-center gap-1"><span className="w-3 h-2 bg-red-300 inline-block rounded-sm" /> Impayé</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${fmt(v)}€`} width={70} />
              <Tooltip formatter={(v: unknown) => fmtEur(v as number)} />
              <Area type="monotone" dataKey="Attendu" stroke="#BFDBFE" fill="#DBEAFE" strokeWidth={1.5} />
              <Area type="monotone" dataKey="Encaissé" stroke="#3B82F6" fill="#93C5FD" strokeWidth={2} />
              <Area type="monotone" dataKey="Impayé" stroke="#EF4444" fill="#FCA5A5" strokeWidth={1.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-900 mb-4">Occupation du parc</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={occupancyData} cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                dataKey="value" startAngle={90} endAngle={-270}>
                <Cell fill="#3B82F6" />
                <Cell fill="#E5E7EB" />
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="text-center -mt-2">
            <p className="text-3xl font-bold text-gray-900">{stats.occupancy.occupancy_rate}%</p>
            <p className="text-sm text-gray-500">Occupation</p>
          </div>
          <div className="flex justify-around mt-3 text-center">
            <div>
              <p className="text-lg font-bold text-blue-600">{stats.occupancy.occupied_units}</p>
              <p className="text-xs text-gray-400">{stats.occupancy.occupied_units > 1 ? 'Occupées' : 'Occupée'}</p>
            </div>
            <div>
              <p className="text-lg font-bold text-gray-400">{stats.occupancy.vacant_units}</p>
              <p className="text-xs text-gray-400">{stats.occupancy.vacant_units > 1 ? 'Vacantes' : 'Vacante'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Comparaison bar chart */}
      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold text-gray-900 mb-4">Encaissé vs Attendu : comparaison mensuelle</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={monthlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${fmt(v)}€`} width={70} />
            <Tooltip formatter={(v: unknown) => fmtEur(v as number)} />
            <Bar dataKey="Attendu" fill="#DBEAFE" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Encaissé" fill="#3B82F6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Ventilation par propriétaire (mandataire) */}
      {isMandataire && stats.by_owner && stats.by_owner.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <KeyRound size={16} className="text-blue-600" /> Ventilation par propriétaire
          </h2>
          <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
            {stats.by_owner.map(o => (
              <div key={o.owner_name} className="flex items-center gap-4">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
                  <KeyRound size={14} className="text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-900 truncate">{o.owner_name}</p>
                    <span className="text-sm font-semibold text-gray-900 ml-2 shrink-0">{fmtEur(o.monthly_revenue)}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{o.properties_count} bien{o.properties_count > 1 ? 's' : ''}</span>
                    <span>· {o.occupied_count} occupé{o.occupied_count > 1 ? 's' : ''}</span>
                    {o.outstanding > 0 && <span className="text-red-500">· Impayés {fmtEur(o.outstanding)}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Maintenances importantes à venir */}
      {stats.upcoming_entretiens && stats.upcoming_entretiens.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Wrench size={16} className="text-blue-600" /> Maintenances à venir
            </h2>
            <button onClick={() => navigate('/entretiens')}
              className="text-xs font-medium text-blue-600 hover:text-blue-800">
              Tout voir →
            </button>
          </div>
          <div className="space-y-2.5">
            {stats.upcoming_entretiens.map(e => {
              const d = new Date(e.scheduled_date)
              const dateLabel = d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
              return (
                <button key={e.id} onClick={() => navigate('/entretiens')}
                  className="w-full flex items-center gap-3 text-left rounded-lg px-2 py-2 hover:bg-gray-50">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${e.overdue ? 'bg-red-100' : 'bg-blue-100'}`}>
                    <Wrench size={14} className={e.overdue ? 'text-red-600' : 'text-blue-600'} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{e.title}</p>
                    {e.property_label && <p className="text-xs text-gray-400 truncate">{e.property_label}</p>}
                  </div>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${e.overdue ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                    {e.overdue ? `En retard · ${dateLabel}` : dateLabel}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
