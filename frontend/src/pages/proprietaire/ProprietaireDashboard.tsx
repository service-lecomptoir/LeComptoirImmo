import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, CreditCard, TrendingUp, ArrowRight, Home } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { propertiesApi } from '@/api/properties'
import { apiClient } from '@/api/client'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' €'

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
  color: 'blue' | 'green' | 'purple' | 'orange'
  onClick?: () => void
}) {
  const colorMap = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
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

export default function ProprietaireDashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [properties, setProperties] = useState<any[]>([])
  const [stats, setStats] = useState<{ monthly_revenue_expected: number; monthly_revenue_received: number; active_leases: number } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const today = new Date()

  useEffect(() => {
    setIsLoading(true)
    const loadProps = propertiesApi.list({ limit: 100 })
      .then(r => setProperties((r.data as any).items ?? r.data))
      .catch(() => setProperties([]))

    const loadStats = apiClient.get('/dashboard/proprietaire-stats')
      .then(r => setStats(r.data))
      .catch(() => {})

    Promise.all([loadProps, loadStats]).finally(() => setIsLoading(false))
  }, [])

  const totalUnits = properties.reduce((s, p) => s + (p.unit_count ?? 0), 0)
  const occupiedUnits = properties.reduce((s, p) => s + (p.occupied_count ?? 0), 0)
  const monthlyRevenue = stats?.monthly_revenue_received ?? 0

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mon tableau de bord</h1>
        <p className="text-gray-500 text-sm mt-1">
          Bienvenue, <span className="font-medium text-gray-700">{user?.full_name}</span>
          {' '}— {format(today, 'd MMMM yyyy', { locale: fr })}
        </p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={Building2}
          label="Mes biens"
          value={isLoading ? '…' : properties.length}
          color="blue"
          onClick={() => navigate('/proprietaire/biens')}
        />
        <StatCard
          icon={Home}
          label={occupiedUnits > 1 ? 'Biens occupés' : 'Bien occupé'}
          value={isLoading ? '…' : occupiedUnits}
          sub={totalUnits > 0 ? `${totalUnits} au total` : undefined}
          color="green"
          onClick={() => navigate('/proprietaire/biens')}
        />
        <StatCard
          icon={CreditCard}
          label="Revenus mensuels"
          value={isLoading ? '…' : fmtEuro(monthlyRevenue)}
          sub="Encaissé ce mois"
          color="purple"
          onClick={() => navigate('/proprietaire/revenus')}
        />
        <StatCard
          icon={TrendingUp}
          label="Taux d'occupation"
          value={isLoading ? '…' : totalUnits > 0 ? `${Math.round((occupiedUnits / totalUnits) * 100)} %` : ''}
          color="orange"
        />
      </div>

      {/* Liste des biens */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900">Mes biens en gestion</h2>
          <button
            onClick={() => navigate('/proprietaire/biens')}
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
          >
            Voir tous <ArrowRight size={11} />
          </button>
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-400 text-center py-6">Chargement…</p>
        ) : properties.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Building2 size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucun bien enregistré</p>
            <p className="text-xs mt-1">Contactez votre gestionnaire pour lier vos biens à votre compte.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {properties.slice(0, 5).map((p: any) => (
              <div
                key={p.id}
                onClick={() => navigate('/proprietaire/biens')}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center">
                    <Building2 size={14} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{p.name}</p>
                    <p className="text-xs text-gray-500">{p.city}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    p.is_occupied ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                  }`}>
                    {p.is_occupied ? 'Occupé' : 'Disponible'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
