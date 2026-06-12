import { useState, useEffect, useCallback, Fragment } from 'react'
import { getErrorMessage } from '@/utils/errors'
import { CreditCard, Search, Filter, FileDown, Send, CheckCircle2, Mail, Trash2, RefreshCw, ChevronRight, ChevronDown } from 'lucide-react'
import { paymentsApi, lettersApi } from '@/api/payments'
import { docFilename } from '@/utils/filename'
import { isMultiMonth } from '@/utils/period'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { PAYMENT_STATUS_LABELS, PAYMENT_STATUS_VARIANTS } from '@/types/payment'
import type { PaymentListItem, PaymentStatus } from '@/types/payment'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { useForm } from 'react-hook-form'
import { toast } from '@/store/toast'

interface RecordForm {
  amount_paid: number
  payment_date: string
  payment_method: string
  notes: string
}

export default function PaymentList() {
  const today = new Date()
  const [payments, setPayments] = useState<PaymentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState<PaymentStatus | ''>('')
  const [filterYear, setFilterYear] = useState(today.getFullYear())
  const [filterMonth, setFilterMonth] = useState(today.getMonth() + 1)
  const [isLoading, setIsLoading] = useState(true)
  const [recordingId, setRecordingId] = useState<string | null>(null)

  const [sendingQuittanceId, setSendingQuittanceId] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [validatingId, setValidatingId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState('')

  const { register, handleSubmit, reset, formState: { isSubmitting } } = useForm<RecordForm>({
    defaultValues: {
      payment_date: format(today, 'yyyy-MM-dd'),
      payment_method: 'virement',
    },
  })

  const fetchPayments = useCallback(
    async (q: string, status: PaymentStatus | '', year: number, month: number) => {
      setIsLoading(true)
      try {
        const { data } = await paymentsApi.list({
          search: q || undefined,
          status: status || undefined,
          year,
          month,
          limit: 100,
        })
        setPayments(data.items)
        setTotal(data.total)
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  // Auto-génère les paiements manquants à chaque changement de mois/année
  useEffect(() => {
    paymentsApi.generate(filterYear, filterMonth).catch(() => {})
  }, [filterYear, filterMonth])

  useEffect(() => {
    const t = setTimeout(
      () => fetchPayments(search, filterStatus, filterYear, filterMonth),
      300
    )
    return () => clearTimeout(t)
  }, [search, filterStatus, filterYear, filterMonth, fetchPayments])

  const handleRecord = async (form: RecordForm) => {
    if (!recordingId) return
    await paymentsApi.record(recordingId, {
      amount_paid: Number(form.amount_paid),
      payment_date: form.payment_date,
      payment_method: form.payment_method || undefined,
      notes: form.notes || undefined,
    })
    setRecordingId(null)
    reset()
    fetchPayments(search, filterStatus, filterYear, filterMonth)
    toast.success('Paiement enregistré')
  }

  const handleDownloadQuittance = async (p: PaymentListItem) => {
    setDownloadingId(p.id)
    try {
      await paymentsApi.downloadQuittance(
        p.id,
        docFilename('quittance', { tenant: p.tenant_full_name, property: p.property_name, month: p.period_month, year: p.period_year })
      )
      // Rafraîchir pour mettre à jour quittance_generated_at
      fetchPayments(search, filterStatus, filterYear, filterMonth)
    } finally {
      setDownloadingId(null)
    }
  }

  const handleSendQuittance = async (p: PaymentListItem) => {
    setSendingQuittanceId(p.id)
    try {
      await paymentsApi.sendQuittance(p.id)
      setSuccessMsg(`Quittance marquée comme envoyée : ${p.tenant_full_name} (${p.period_label})`)
      setTimeout(() => setSuccessMsg(''), 4000)
      fetchPayments(search, filterStatus, filterYear, filterMonth)
    } finally {
      setSendingQuittanceId(null)
    }
  }

  const handleValidateDeclaration = async (p: PaymentListItem) => {
    setValidatingId(p.id)
    try {
      await paymentsApi.validateDeclaration(p.id)
      setSuccessMsg(`Paiement validé : ${p.tenant_full_name} (${p.period_label})`)
      setTimeout(() => setSuccessMsg(''), 4000)
      fetchPayments(search, filterStatus, filterYear, filterMonth)
    } catch (e: any) {
      alert(getErrorMessage(e, 'Erreur lors de la validation'))
    } finally {
      setValidatingId(null)
    }
  }

  const handleRefuseDeclaration = async (p: PaymentListItem) => {
    if (!confirm(`Refuser la déclaration de paiement de ${p.tenant_full_name} : ${p.period_label} ?\nLe locataire en sera informé.`)) return
    setValidatingId(p.id)
    try {
      await paymentsApi.refuseDeclaration(p.id)
      setSuccessMsg(`Déclaration refusée : ${p.tenant_full_name} (${p.period_label})`)
      setTimeout(() => setSuccessMsg(''), 4000)
      fetchPayments(search, filterStatus, filterYear, filterMonth)
    } catch (e: any) {
      alert(getErrorMessage(e, 'Erreur lors du refus'))
    } finally {
      setValidatingId(null)
    }
  }

  const declaredMethodLabel = (m?: string | null) =>
    m === 'especes' ? 'Espèces' : m === 'virement' ? 'Virement' : (m ?? '')

  const methodLabel = (m?: string | null) => {
    switch (m) {
      case 'virement': return 'Virement bancaire'
      case 'cheque': return 'Chèque'
      case 'prelevement': return 'Prélèvement automatique'
      case 'especes': return 'Espèces'
      default: return m || 'Versement'
    }
  }

  // Détail des mouvements composant le montant payé (dérivé des champs du paiement)
  const paymentEntries = (p: PaymentListItem) => {
    const apl = p.amount_apl ?? 0
    const credit = p.credit_applied ?? 0
    const versement = Math.round((p.amount_paid - apl - credit) * 100) / 100
    const rows: { label: string; date?: string | null; amount: number }[] = []
    if (apl > 0) rows.push({ label: 'Aide au logement (tiers-payant CAF)', amount: apl })
    if (credit > 0) rows.push({ label: 'Avance déduite (trop-perçu antérieur)', amount: credit })
    if (versement > 0.009) rows.push({ label: `Versement : ${methodLabel(p.payment_method)}`, date: p.payment_date, amount: versement })
    return rows
  }

  const fmtEuro = (n: number) =>
    n.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €'

  const months = [
    '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
  ]

  const recordingPayment = payments.find(p => p.id === recordingId)

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Paiements</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} enregistrement{total > 1 ? 's' : ''}</p>
        </div>
      </div>

      {successMsg && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-green-50 text-green-800 text-sm border border-green-200 flex items-center gap-2">
          <CheckCircle2 size={15} className="text-green-600 shrink-0" />
          {successMsg}
        </div>
      )}

      {/* Filtres */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={filterMonth}
          onChange={e => setFilterMonth(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
        >
          {months.slice(1).map((m, i) => (
            <option key={i + 1} value={i + 1}>{m}</option>
          ))}
        </select>
        <select
          value={filterYear}
          onChange={e => setFilterYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
        >
          {[today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <div className="flex items-center gap-2 px-3 py-2 border border-gray-300 rounded-lg text-sm">
          <Filter size={13} className="text-gray-400" />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value as PaymentStatus | '')}
            className="outline-none bg-transparent text-gray-700 cursor-pointer"
          >
            <option value="">Tous statuts</option>
            {(Object.entries(PAYMENT_STATUS_LABELS) as [PaymentStatus, string][]).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full min-w-[640px]">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Locataire</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Bien</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Période</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Dû</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Payé</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Solde</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Statut</th>
              <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Quittance</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={9} className="text-center py-12 text-sm text-gray-500">Chargement...</td></tr>
            ) : payments.length === 0 ? (
              <tr>
                <td colSpan={9}>
                  <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                    <CreditCard size={32} className="text-gray-300 mb-2" />
                    <p className="text-sm">Aucun paiement : cliquez sur "Générer" pour créer les loyers du mois</p>
                  </div>
                </td>
              </tr>
            ) : (
              payments.map(p => (
                <Fragment key={p.id}>
                <tr className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    <button
                      onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
                      className="inline-flex items-center gap-1.5 text-left hover:text-blue-600"
                      title="Voir le détail des règlements"
                    >
                      {expandedId === p.id
                        ? <ChevronDown size={14} className="text-gray-400 shrink-0" />
                        : <ChevronRight size={14} className="text-gray-400 shrink-0" />}
                      {p.tenant_full_name}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-900">{p.property_name}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {p.period_label}
                    {isMultiMonth(p.period_start, p.period_end) && p.period_range_label && (
                      <div className="text-xs text-gray-500">{p.period_range_label}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-900">{fmtEuro(p.amount_due)}</td>
                  <td className="px-4 py-3 text-sm text-right text-green-700">
                    {fmtEuro(p.amount_paid)}
                    {p.credit_applied != null && p.credit_applied > 0 && (
                      <div className="text-[11px] text-blue-500">dont avance {fmtEuro(p.credit_applied)}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-semibold">
                    {p.balance > 0 ? (
                      <span className="text-red-600">{fmtEuro(p.balance)}</span>
                    ) : p.amount_paid > p.amount_due ? (
                      <span className="text-green-600" title="Trop-perçu (avance)">+{fmtEuro(p.amount_paid - p.amount_due)}</span>
                    ) : (
                      <span className="text-gray-400"></span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      label={PAYMENT_STATUS_LABELS[p.status]}
                      variant={PAYMENT_STATUS_VARIANTS[p.status]}
                      dot
                    />
                    {p.declared_at && p.status !== 'paid' && (
                      <div className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5 whitespace-nowrap">
                        Déclaré · {declaredMethodLabel(p.declared_method)}
                        {p.declared_amount != null && ` · ${fmtEuro(p.declared_amount)}`}
                      </div>
                    )}
                  </td>

                  {/* Colonne quittance : uniquement si le mois est intégralement payé */}
                  <td className="px-4 py-3">
                    {p.status === 'paid' ? (
                      <div className="flex items-center gap-2">
                        {/* Télécharger */}
                        <button
                          onClick={() => handleDownloadQuittance(p)}
                          disabled={downloadingId === p.id}
                          className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-blue-600 disabled:opacity-50"
                          title="Télécharger la quittance PDF"
                        >
                          {downloadingId === p.id
                            ? <RefreshCw size={14} className="animate-spin" />
                            : <FileDown size={14} />
                          }
                        </button>

                        {/* Envoyer / marquer envoyée */}
                        <button
                          onClick={() => handleSendQuittance(p)}
                          disabled={sendingQuittanceId === p.id}
                          title={p.quittance_sent_at
                            ? `Marquée envoyée le ${format(new Date(p.quittance_sent_at), 'd MMM yyyy', { locale: fr })}`
                            : 'Marquer la quittance comme envoyée'}
                          className={`p-1.5 rounded disabled:opacity-50 transition-colors ${
                            p.quittance_sent_at
                              ? 'text-green-600 bg-green-50 hover:bg-green-100'
                              : 'text-gray-400 hover:bg-gray-100 hover:text-blue-600'
                          }`}
                        >
                          {sendingQuittanceId === p.id
                            ? <RefreshCw size={14} className="animate-spin" />
                            : p.quittance_sent_at
                              ? <CheckCircle2 size={14} />
                              : <Mail size={14} />
                          }
                        </button>

                        {/* Disponible = consultable par le locataire dans son espace */}
                        {p.quittance_generated_at && !p.quittance_sent_at && (
                          <span className="text-xs text-green-600 whitespace-nowrap" title="Consultable par le locataire dans son espace">Disponible</span>
                        )}
                        {p.quittance_sent_at && (
                          <span className="text-xs text-green-600 whitespace-nowrap" title="Quittance marquée comme envoyée">Envoyée</span>
                        )}
                      </div>
                    ) : null}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      {p.declared_at && ['pending', 'partial', 'late'].includes(p.status) && (
                        <>
                          <button
                            onClick={() => handleValidateDeclaration(p)}
                            disabled={validatingId === p.id}
                            className="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                            title={`Valider le règlement déclaré par le locataire (${declaredMethodLabel(p.declared_method)})`}
                          >
                            {validatingId === p.id
                              ? <RefreshCw size={12} className="animate-spin" />
                              : <CheckCircle2 size={12} />}
                            Valider
                          </button>
                          <button
                            onClick={() => handleRefuseDeclaration(p)}
                            disabled={validatingId === p.id}
                            className="px-2 py-1 text-xs font-medium text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50"
                            title="Refuser la déclaration de paiement"
                          >
                            Refuser
                          </button>
                        </>
                      )}
                      {['pending', 'partial', 'late'].includes(p.status) && (
                        <button
                          onClick={() => { setRecordingId(p.id); reset({ payment_date: format(today, 'yyyy-MM-dd'), payment_method: 'virement' }) }}
                          className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100"
                        >
                          Saisir
                        </button>
                      )}
                      {['pending', 'partial', 'late'].includes(p.status) && (
                        <button
                          onClick={() => lettersApi.downloadRelance(p.id, docFilename('relance', { tenant: p.tenant_full_name, property: p.property_name, month: p.period_month, year: p.period_year }))}
                          className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700"
                          title="Lettre de relance"
                        >
                          <Send size={14} />
                        </button>
                      )}
                      <button
                        onClick={async () => {
                          if (!confirm(`Supprimer le paiement de ${p.tenant_full_name} : ${p.period_label} ?\nCette action est irréversible.`)) return
                          try {
                            await paymentsApi.delete(p.id)
                            fetchPayments(search, filterStatus, filterYear, filterMonth)
                          } catch (e: any) {
                            alert(getErrorMessage(e, 'Erreur lors de la suppression'))
                          }
                        }}
                        title="Supprimer ce paiement"
                        className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-red-600"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
                {expandedId === p.id && (
                  <tr className="bg-blue-50/40">
                    <td colSpan={9} className="px-4 py-3">
                      <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-2">
                        Détail des règlements
                      </p>
                      {paymentEntries(p).length === 0 ? (
                        <p className="text-sm text-gray-400">Aucun versement enregistré pour l'instant.</p>
                      ) : (
                        <div className="space-y-1 max-w-xl">
                          {paymentEntries(p).map((e, i) => (
                            <div key={i} className="flex items-center justify-between gap-4 text-sm">
                              <span className="text-gray-700">
                                {e.label}
                                {e.date ? ` · ${format(new Date(e.date), 'd MMM yyyy', { locale: fr })}` : ''}
                              </span>
                              <span className="font-medium text-gray-900 whitespace-nowrap">{fmtEuro(e.amount)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="mt-2 pt-2 border-t border-gray-200 space-y-1 max-w-xl">
                        <div className="flex items-center justify-between gap-4 text-sm">
                          <span className="font-semibold text-gray-700">Total versé</span>
                          <span className="font-bold text-gray-900">{fmtEuro(p.amount_paid)}</span>
                        </div>
                        {p.balance > 0 && (
                          <div className="flex items-center justify-between gap-4 text-sm">
                            <span className="text-red-600">Reste à payer</span>
                            <span className="font-semibold text-red-600">{fmtEuro(p.balance)}</span>
                          </div>
                        )}
                        {p.amount_paid > p.amount_due && (
                          <div className="flex items-center justify-between gap-4 text-sm">
                            <span className="text-green-600">Avance (trop-perçu)</span>
                            <span className="font-semibold text-green-600">+{fmtEuro(p.amount_paid - p.amount_due)}</span>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
                </Fragment>
              ))
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Modal saisie paiement */}
      {recordingId && (
        <Modal
          isOpen
          onClose={() => { setRecordingId(null); reset() }}
          title="Saisir un paiement"
          size="sm"
          footer={
            <>
              <button
                onClick={() => { setRecordingId(null); reset() }}
                className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                onClick={handleSubmit(handleRecord)}
                disabled={isSubmitting}
                className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Enregistrement...' : 'Enregistrer'}
              </button>
            </>
          }
        >
          {recordingPayment && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
              <strong>{recordingPayment.tenant_full_name}</strong> : {recordingPayment.period_label}<br />
              Solde restant : <strong>{fmtEuro(recordingPayment.balance)}</strong>
            </div>
          )}
          <form className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Montant encaissé (€) *</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                {...register('amount_paid')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Date de réception *</label>
              <input
                type="date"
                {...register('payment_date')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Mode de paiement</label>
              <select
                {...register('payment_method')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="virement">Virement bancaire</option>
                <option value="cheque">Chèque</option>
                <option value="prelevement">Prélèvement</option>
                <option value="especes">Espèces</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Notes</label>
              <input
                {...register('notes')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
