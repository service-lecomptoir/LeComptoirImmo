import { useAuthStore } from '@/store/authStore'

export default function Dashboard() {
  const { user } = useAuthStore()

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
        <p className="text-gray-500 text-sm mt-1">
          Bienvenue, <span className="font-medium text-gray-700">{user?.full_name}</span>
        </p>
      </div>

      {/* KPI Cards — placeholder Phase 8 */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Locataires actifs', value: '—', color: 'blue' },
          { label: 'Biens gérés', value: '—', color: 'green' },
          { label: 'Loyers du mois', value: '—', color: 'purple' },
          { label: 'Impayés', value: '—', color: 'red' },
        ].map((card) => (
          <div
            key={card.label}
            className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm"
          >
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <p className="text-sm text-gray-500 text-center py-8">
          Le tableau de bord complet sera disponible en <strong>Phase 8</strong>.<br />
          Les modules sont développés progressivement.
        </p>
      </div>
    </div>
  )
}
