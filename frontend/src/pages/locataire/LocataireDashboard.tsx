import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Home, CreditCard, FileText, ArrowRight, Download, Wallet, CheckCircle,
  Receipt, MessagesSquare, Megaphone, Bell, Building2, Mail, Phone, MapPin,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { getDayMoment, formatLongDate } from '@/lib/dayMoment'
import { apiClient } from '@/api/client'
import { leasesApi } from '@/api/leases'
import { paymentsApi } from '@/api/payments'
import { ticketsApi } from '@/api/tickets'
import { signalementsApi } from '@/api/signalements'
import { usersApi, type ManagerContact } from '@/api/users'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Button } from '@/components/ui'
import { formatEuro as fmtEuro } from '@/utils/format'
import { docFilename } from '@/utils/filename'

export default function LocataireDashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [lease, setLease] = useState<any>(null)
  const [current, setCurrent] = useState<any>(null)
  const [lastPayment, setLastPayment] = useState<any>(null)
  const [lastQuittance, setLastQuittance] = useState<any>(null)
  const [openTickets, setOpenTickets] = useState(0)
  const [openSignalements, setOpenSignalements] = useState(0)
  const [manager, setManager] = useState<ManagerContact | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [leasesRes, curRes, paymentsRes, ticketsRes, signRes, mgrRes] = await Promise.allSettled([
          leasesApi.list({ is_active: true, limit: 1 }),
          apiClient.get('/payments/locataire/current'),
          paymentsApi.list({ limit: 12 }),
          ticketsApi.mine(),
          signalementsApi.mine(),
          usersApi.myManager(),
        ])

        if (leasesRes.status === 'fulfilled') {
          const items = leasesRes.value.data.items ?? leasesRes.value.data
          setLease(items?.[0] ?? null)
        }
        if (curRes.status === 'fulfilled') setCurrent(curRes.value.data.payment ?? null)
        if (paymentsRes.status === 'fulfilled') {
          const items = paymentsRes.value.data.items ?? paymentsRes.value.data
          setLastPayment(items?.[0] ?? null)
          setLastQuittance((items ?? []).find((p: any) => p.status === 'paid') ?? null)
        }
        if (ticketsRes.status === 'fulfilled') {
          setOpenTickets(ticketsRes.value.data.filter(
            (t) => ['open', 'in_progress', 'pending_closure'].includes(t.status)).length)
        }
        if (signRes.status === 'fulfilled') {
          setOpenSignalements(signRes.value.data.filter(
            (s) => ['nouveau', 'en_cours'].includes(s.status)).length)
        }
        if (mgrRes.status === 'fulfilled') setManager(mgrRes.value.data)
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  const due = Number(current?.balance ?? current?.amount_due) || 0
  const aPayer = due > 0.005

  const quickLinks = [
    { icon: CreditCard, label: 'Payer mon loyer', to: '/locataire/payer', color: 'bg-blue-50 text-blue-600' },
    { icon: Wallet, label: 'Ma comptabilité', to: '/locataire/paiements', color: 'bg-green-50 text-green-600' },
    { icon: FileText, label: 'Mes documents', to: '/locataire/documents', color: 'bg-purple-50 text-purple-600' },
    { icon: MessagesSquare, label: 'Mes démarches', to: '/locataire/demarches', color: 'bg-amber-50 text-amber-600' },
    { icon: Megaphone, label: 'Signaler', to: '/locataire/signaler', color: 'bg-red-50 text-red-600' },
    { icon: Bell, label: 'Avis d\'échéance', to: '/locataire/avis-echeances', color: 'bg-sky-50 text-sky-600' },
  ]

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mon espace</h1>
          <p className="text-gray-500 text-sm mt-1">
            Bonjour, <span className="font-medium text-gray-700">{user?.full_name}</span>
          </p>
        </div>
        {(() => {
          const m = getDayMoment()
          const { Icon } = m
          return (
            <div className="flex items-center gap-2.5">
              <span className="w-9 h-9 rounded-full flex items-center justify-center shrink-0" style={{ background: m.bg }} title={m.label}>
                <Icon size={18} style={{ color: m.color }} />
              </span>
              <div>
                <p className="text-xs font-medium text-gray-600 leading-tight">{m.label}</p>
                <p className="text-sm text-gray-500 capitalize">{formatLongDate()}</p>
              </div>
            </div>
          )
        })()}
      </div>

      {/* Prochaine échéance / solde — bloc d'action principal */}
      <div className={`rounded-xl border p-5 mb-5 ${aPayer ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'}`}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${aPayer ? 'bg-amber-100' : 'bg-green-100'}`}>
              {aPayer ? <Wallet size={20} className="text-amber-600" /> : <CheckCircle size={20} className="text-green-600" />}
            </div>
            <div>
              {isLoading ? (
                <p className="text-sm text-gray-400">Chargement…</p>
              ) : aPayer ? (
                <>
                  <p className="text-xs uppercase tracking-wide font-medium text-gray-500">Loyer à régler</p>
                  <p className="text-2xl font-bold text-red-600 leading-tight">{fmtEuro(due)}</p>
                  {lease?.payment_day && (
                    <p className="text-xs text-gray-500 mt-0.5">Échéance le {lease.payment_day} du mois</p>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm font-semibold text-gray-800">Vous êtes à jour</p>
                  <p className="text-xs text-gray-500 mt-0.5">Aucun loyer à régler pour le moment</p>
                </>
              )}
            </div>
          </div>
          <Button
            variant={aPayer ? 'primary' : 'secondary'}
            onClick={() => navigate('/locataire/payer')}
            leftIcon={<CreditCard size={16} />}
          >
            {aPayer ? 'Payer mon loyer' : 'Voir mes paiements'}
          </Button>
        </div>
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
                onClick={() => leasesApi.downloadPdf(lease.id, docFilename(lease.lease_type === 'meuble' ? 'bail_meuble' : 'bail_non_meuble', { tenant: lease.tenant_full_name, property: lease.property_name }))}
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
                <>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Aide personnelle au logement (tiers-payant)</span>
                    <span className="text-green-600 font-medium">
                      {lease.apl_amount ? `− ${fmtEuro(lease.apl_amount)} / mois` : 'Oui'}
                    </span>
                  </div>
                  {lease.apl_amount ? (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Reste à votre charge</span>
                      <span className="font-semibold text-gray-900">
                        {fmtEuro(Math.max(0, lease.rent_amount + lease.charges_amount - lease.apl_amount))} / mois
                      </span>
                    </div>
                  ) : null}
                </>
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

      {/* Quittance récente · Suivi des demandes · Mon gestionnaire */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-5">
        {/* Quittance récente */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <Receipt size={15} className="text-green-600" />
            Quittance récente
          </h2>
          {isLoading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : !lastQuittance ? (
            <p className="text-sm text-gray-400">Aucune quittance disponible pour le moment.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Période</span>
                <span className="font-medium text-gray-900">{lastQuittance.period_label}</span>
              </div>
              <Button
                variant="secondary"
                size="sm"
                fullWidth
                leftIcon={<Download size={14} />}
                onClick={() => paymentsApi.downloadQuittance(lastQuittance.id,
                  docFilename('quittance', { tenant: lastQuittance.tenant_full_name, property: lastQuittance.property_name, month: lastQuittance.period_month, year: lastQuittance.period_year }))}
              >
                Télécharger la quittance
              </Button>
            </div>
          )}
        </div>

        {/* Suivi des demandes */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <MessagesSquare size={15} className="text-amber-600" />
            Mes demandes en cours
          </h2>
          <div className="space-y-2">
            <button
              onClick={() => navigate('/locataire/demarches')}
              className="w-full flex items-center justify-between gap-2 rounded-lg border border-gray-200 px-3 py-2.5 hover:bg-gray-50 transition-colors text-left"
            >
              <span className="text-sm text-gray-700 flex items-center gap-2"><MessagesSquare size={14} className="text-amber-600" /> Démarches</span>
              <span className="flex items-center gap-2">
                {openTickets > 0
                  ? <StatusBadge label={`${openTickets} en cours`} variant="yellow" />
                  : <span className="text-xs text-gray-400">À jour</span>}
                <ArrowRight size={13} className="text-gray-400" />
              </span>
            </button>
            <button
              onClick={() => navigate('/locataire/signaler')}
              className="w-full flex items-center justify-between gap-2 rounded-lg border border-gray-200 px-3 py-2.5 hover:bg-gray-50 transition-colors text-left"
            >
              <span className="text-sm text-gray-700 flex items-center gap-2"><Megaphone size={14} className="text-red-600" /> Signalements</span>
              <span className="flex items-center gap-2">
                {openSignalements > 0
                  ? <StatusBadge label={`${openSignalements} en cours`} variant="red" />
                  : <span className="text-xs text-gray-400">Aucun</span>}
                <ArrowRight size={13} className="text-gray-400" />
              </span>
            </button>
          </div>
        </div>

        {/* Mon gestionnaire */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <Building2 size={15} className="text-blue-600" />
            Mon gestionnaire
          </h2>
          {isLoading ? (
            <p className="text-sm text-gray-400">Chargement…</p>
          ) : !manager ? (
            <p className="text-sm text-gray-400">Coordonnées non disponibles.</p>
          ) : (
            <div className="space-y-2.5 text-sm">
              <p className="font-medium text-gray-900">{manager.full_name}</p>
              {manager.email && (
                <a href={`mailto:${manager.email}`} className="flex items-center gap-2 text-gray-600 hover:text-blue-600 break-all">
                  <Mail size={13} className="text-gray-400 shrink-0" /> {manager.email}
                </a>
              )}
              {manager.phone && (
                <a href={`tel:${manager.phone.replace(/\s+/g, '')}`} className="flex items-center gap-2 text-gray-600 hover:text-blue-600">
                  <Phone size={13} className="text-gray-400 shrink-0" /> {manager.phone}
                </a>
              )}
              {manager.address && (
                <p className="flex items-start gap-2 text-gray-500">
                  <MapPin size={13} className="text-gray-400 shrink-0 mt-0.5" /> <span className="whitespace-pre-line">{manager.address}</span>
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Liens rapides */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mt-5">
        {quickLinks.map(item => (
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
