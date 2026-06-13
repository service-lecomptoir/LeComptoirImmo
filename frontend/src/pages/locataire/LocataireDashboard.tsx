import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Home, CreditCard, FileText,
  ArrowRight, Download,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { leasesApi } from '@/api/leases'
import { paymentsApi } from '@/api/payments'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { StatusBadge } from '@/components/common/StatusBadge'
import { docFilename } from '@/utils/filename'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

export default function LocataireDashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [lease, setLease] = useState<any>(null)
  const [lastPayment, setLastPayment] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const today = new Date()

  useEffect(() => {
    const load = async () => {
      try {
        const [leasesRes, paymentsRes] = await Promise.allSettled([
          leasesApi.list({ is_active: true, limit: 1 }),
          paymentsApi.list({ limit: 3 }),
        ])

        if (leasesRes.status === 'fulfilled') {
          const items = leasesRes.value.data.items ?? leasesRes.value.data
          setLease(items?.[0] ?? null)
        }
        if (paymentsRes.status === 'fulfilled') {
          const items = paymentsRes.value.data.items ?? paymentsRes.value.data
          setLastPayment(items?.[0] ?? null)
        }
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mon espace</h1>
        <p className="text-gray-500 text-sm mt-1">
          Bonjour, <span className="font-medium text-gray-700">{user?.full_name}</span>
          {' '}— {format(today, 'd MMMM yyyy', { locale: fr })}
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Mon bail */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Home size={15} className="text-blue-600" />
              Mon bail
            </h2>
            {lease && (
              <button
                onClick={() => leasesApi.downloadPdf(lease.id, docFilename('bail_non_meuble', { tenant: lease.tenant_full_name, property: lease.property_name }))}
                className="flex items-center gap-1.5 text-xs text-blue-600 hover:bg-blue-50 px-2.5 py-1.5 rounded-lg border border-blue-200 transition-colors"
              >
                <Download size={12} />
                Télécharger le bail
              </button>
            )}
          </div>
          {isLoading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : !lease ? (
            <p className="text-sm text-gray-400">Aucun bail actif trouvé</p>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Bien</span>
                <span className="font-medium text-gray-900">{lease.property_name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Loyer + charges</span>
                <span className="font-semibold text-gray-900">
                  {fmtEuro(lease.rent_amount + lease.charges_amount)} / mois
                </span>
              </div>
              {lease.apl_tiers_payant && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Aide personnelle au logement (tiers-payant)</span>
                  <span className="text-green-600 font-medium">Oui</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Début du bail</span>
                <span className="font-medium text-gray-900">
                  {lease.start_date
                    ? format(new Date(lease.start_date), 'd MMM yyyy', { locale: fr })
                    : ''}
                </span>
              </div>
              {lease.payment_day && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Jour de paiement</span>
                  <span className="font-medium text-gray-900">Le {lease.payment_day} du mois</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dernier paiement */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <CreditCard size={15} className="text-green-600" />
              Dernier paiement
            </h2>
            <button
              onClick={() => navigate('/locataire/paiements')}
              className="text-xs text-blue-600 hover:underline flex items-center gap-1"
            >
              Voir tous <ArrowRight size={11} />
            </button>
          </div>
          {isLoading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : !lastPayment ? (
            <p className="text-sm text-gray-400">Aucun paiement enregistré</p>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Période</span>
                <span className="font-medium text-gray-900">{lastPayment.period_label}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Montant dû</span>
                <span className="font-medium text-gray-900">{fmtEuro(lastPayment.amount_due)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Montant payé</span>
                <span className="font-semibold text-gray-900">{fmtEuro(lastPayment.amount_paid ?? 0)}</span>
              </div>
              {lastPayment.payment_date && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Date</span>
                  <span className="font-medium text-gray-900">
                    {format(new Date(lastPayment.payment_date), 'd MMM yyyy', { locale: fr })}
                  </span>
                </div>
              )}
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-500">Statut</span>
                <StatusBadge
                  label={
                    lastPayment.status === 'paid' ? 'Payé'
                    : lastPayment.status === 'partial' ? 'Partiel'
                    : lastPayment.status === 'pending' ? 'En attente'
                    : lastPayment.status === 'late' ? 'En retard'
                    : lastPayment.status
                  }
                  variant={
                    lastPayment.status === 'paid' ? 'green'
                    : lastPayment.status === 'partial' ? 'yellow'
                    : lastPayment.status === 'pending' ? 'blue'
                    : 'red'
                  }
                  dot
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Liens rapides */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-5">
        {[
          { icon: CreditCard, label: 'Ma comptabilité', to: '/locataire/paiements', color: 'bg-green-50 text-green-600' },
          { icon: FileText, label: 'Mes documents', to: '/locataire/documents', color: 'bg-purple-50 text-purple-600' },
        ].map(item => (
          <button
            key={item.to}
            onClick={() => navigate(item.to)}
            className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md hover:border-gray-300 transition-all text-center"
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-2 ${item.color}`}>
              <item.icon size={18} />
            </div>
            <p className="text-xs font-medium text-gray-700">{item.label}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
