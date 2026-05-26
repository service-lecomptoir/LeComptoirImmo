import { useEffect, useState } from 'react'
import { Users, UserCheck, UserX, Home, Key } from 'lucide-react'
import { dashboardApi } from '@/api/dashboard'
import type { DashboardStats } from '@/types'

interface KpiCardProps {
  label: string
  value: number | string
  icon: React.ElementType
  color: string
  bg: string
}

function KpiCard({ label, value, icon: Icon, color, bg }: KpiCardProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-5">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${bg}`}>
        <Icon size={22} className={color} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dashboardApi.getStats()
      .then(res => setStats(res.data))
      .catch(() => setError('Impossible de charger les statistiques'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
          {error || 'Erreur inconnue'}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Vue globale de la plateforme LeComptoirImmo</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <KpiCard
          label="Gestionnaires actifs"
          value={stats.gestionnaires_actifs}
          icon={UserCheck}
          color="text-emerald-600"
          bg="bg-emerald-50"
        />
        <KpiCard
          label="Gestionnaires bloques"
          value={stats.gestionnaires_bloques}
          icon={UserX}
          color="text-red-600"
          bg="bg-red-50"
        />
        <KpiCard
          label="Proprietaires"
          value={stats.total_proprietaires}
          icon={Key}
          color="text-indigo-600"
          bg="bg-indigo-50"
        />
        <KpiCard
          label="Locataires"
          value={stats.total_locataires}
          icon={Home}
          color="text-violet-600"
          bg="bg-violet-50"
        />
      </div>

      {/* Plans distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-5">Repartition par plan</h2>
          {stats.plans_distribution.length === 0 ? (
            <p className="text-sm text-gray-400">Aucun plan configure</p>
          ) : (
            <div className="space-y-3">
              {stats.plans_distribution.map(plan => (
                <div key={plan.name} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                    <span className="text-sm font-medium text-gray-700">{plan.name}</span>
                  </div>
                  <span className="text-sm text-gray-500 font-mono">
                    {plan.count} gestionnaire{plan.count > 1 ? 's' : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-5">Synthese</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-gray-50">
              <span className="text-sm text-gray-600">Total gestionnaires</span>
              <span className="font-semibold text-gray-900">{stats.total_gestionnaires}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-gray-50">
              <span className="text-sm text-gray-600">Taux de blocage</span>
              <span className="font-semibold text-gray-900">
                {stats.total_gestionnaires > 0
                  ? Math.round((stats.gestionnaires_bloques / stats.total_gestionnaires) * 100)
                  : 0}%
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-gray-50">
              <span className="text-sm text-gray-600">Total utilisateurs</span>
              <span className="font-semibold text-gray-900">
                {stats.total_gestionnaires + stats.total_proprietaires + stats.total_locataires}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
