import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Users, CreditCard, AlertTriangle,
  Home, FileText, ArrowRight,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { paymentsApi } from '@/api/payments'
import { leasesApi } from '@/api/leases'
import type { DashboardStats } from '@/types/payment'
import type { LeaseListItem } from '@/types/lease'
import { StatusBadge } from '@/components/common/StatusBadge'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
  onClick,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  sub?: string
  color: 'blue' | 'green' | 'purple' | 'red' | 'orange'
  onClick?: () => void
}) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    red: 'bg-red-50 text-red-600',
    orange: 'bg-orange-50 text-orange-600',
  }
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-gray-200 p-5 shadow-sm ${onClick ? 'cursor-pointer hover:shadow-md hover:border-blue-200 transition-all' : ''}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorMap[color]}`}>
          <Icon size={20} />
        </div>
        {onClick && <ArrowRight size={14} className="text-gray-300" />}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' €'

export default function Dashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [latestLeases, setLatestLeases] = useState<LeaseListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, leasesRes] = await Promise.all([
          paymentsApi.dashboardStats(),
          leasesApi.list({ is_active: true, limit: 5 }),
        ])
        setStats(statsRes.data)
        setLatestLeases(leasesRes.data.items)
      } catch {
        // silently fail — backend might not be running
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  const today = new Date()
  const month = format(today, 'MMMM yyyy', { locale: fr })

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
        <p className="text-gray-500 text-sm mt-1">
          Bienvenue, <span className="font-medium text-gray-700">{user?.full_name}</span>
          {' '}— {format(today, 'd MMMM yyyy', { locale: fr })}
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={Users}
          label="Locataires"
          value={isLoading ? '…' : stats?.total_tenants ?? '—'}
          color="blue"
          onClick={() => navigate('/tenants')}
        />
        <StatCard
          icon={Home}
          label="Taux d'occupation"
          value={isLoading ? '…' : stats ? `${Math.round(stats.occupancy_rate * 100)} %` : '—'}
          sub={stats ? `${stats.occupied_units} / ${stats.total_units} logements` : undefined}
          color="green"
          onClick={() => navigate('/properties')}
        />
        <StatCard
          icon={CreditCard}
          label={`Loyers ${month}`}
          value={isLoading ? '…' : stats ? fmtEuro(stats.monthly.total_paid) : '—'}
          sub={stats ? `sur ${fmtEuro(stats.monthly.total_due)} attendus` : undefined}
          color="purple"
          onClick={() => navigate('/payments')}
        />
        <StatCard
          icon={AlertTriangle}
          label="Impayés / En retard"
          value={isLoading ? '…' : stats ? String(stats.monthly.late_count + stats.monthly.pending_count) : '—'}
          sub={stats && stats.monthly.total_balance > 0 ? `${fmtEuro(stats.monthly.total_balance)} à encaisser` : undefined}
          color={stats && (stats.monthly.late_count > 0) ? 'red' : 'orange'}
          onClick={() => navigate('/payments')}
        />
      </div>

      {/* Row 2 : stats mensuelles + baux actifs */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* Stats mois */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">
            Paiements — {stats?.monthly.period_label ?? month}
          </h2>
          {isLoading ? (
            <p className="text-sm text-gray-400 text-center py-6">Chargement…</p>
          ) : stats ? (
            <div className="space-y-3">
              {[
                { label: 'Payés', count: stats.monthly.paid_count, variant: 'green', amount: null },
                { label: 'Partiels', count: stats.monthly.partial_count, variant: 'yellow', amount: null },
                { label: 'En attente', count: stats.monthly.pending_count, variant: 'blue', amount: null },
                { label: 'En retard', count: stats.monthly.late_count, variant: 'red', amount: null },
              ]
                .filter(r => r.count > 0)
                .map(r => (
                  <div key={r.label} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <StatusBadge label={r.label} variant={r.variant as any} dot />
                    </div>
                    <span className="text-sm font-semibold text-gray-900">
                      {r.count} bail{r.count > 1 ? 's' : ''}
                    </span>
                  </div>
                ))}
              <div className="pt-3 border-t border-gray-100 flex justify-between">
                <span className="text-sm text-gray-600">Solde à encaisser</span>
                <span className={`text-sm font-bold ${stats.monthly.total_balance > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                  {fmtEuro(stats.monthly.total_balance)}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-6">
              Données non disponibles (backend démarré ?)
            </p>
          )}
        </div>

        {/* Baux actifs récents */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900">Derniers baux actifs</h2>
            <button
              onClick={() => navigate('/leases')}
              className="text-xs text-blue-600 hover:underline flex items-center gap-1"
            >
              Voir tous <ArrowRight size={11} />
            </button>
          </div>
          {isLoading ? (
            <p className="text-sm text-gray-400 text-center py-6">Chargement…</p>
          ) : latestLeases.length === 0 ? (
            <div className="text-center py-6 text-gray-400">
              <FileText size={28} className="mx-auto mb-2 text-gray-300" />
              <p className="text-sm">Aucun bail actif</p>
            </div>
          ) : (
            <div className="space-y-2">
              {latestLeases.map(lease => (
                <div
                  key={lease.id}
                  onClick={() => navigate(`/leases/${lease.id}`)}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900">{lease.tenant_full_name}</p>
                    <p className="text-xs text-gray-500">
                      {lease.property_name} — {lease.unit_ref}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">
                      {fmtEuro(lease.rent_amount + lease.charges_amount)} / mois
                    </p>
                    {lease.apl_tiers_payant && (
                      <p className="text-xs text-green-600">Tiers-payant CAF</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
