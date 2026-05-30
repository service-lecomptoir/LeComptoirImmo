import { useEffect, useState, useCallback } from 'react'
import { FileText, ChevronLeft, ChevronRight, Check, RotateCw, RefreshCw, Download, Pencil, Trash2, Mail } from 'lucide-react'
import { invoicesApi, type Invoice, type InvoiceEdit } from '@/api/invoices'

const MONTHS = [
  'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

function eur(n: number) {
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'
}

interface EditModalProps {
  invoice: Invoice
  onClose: () => void
  onSaved: (inv: Invoice) => void
}

function EditModal({ invoice, onClose, onSaved }: EditModalProps) {
  const [amount, setAmount] = useState(invoice.amount.toString())
  const [planName, setPlanName] = useState(invoice.plan_name ?? '')
  const [year, setYear] = useState(invoice.period_year)
  const [month, setMonth] = useState(invoice.period_month)
  const [status, setStatus] = useState<'paid' | 'unpaid'>(invoice.status)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload: InvoiceEdit = {
        amount: parseFloat(amount) || 0,
        plan_name: planName || null,
        period_year: year,
        period_month: month,
        status,
      }
      const { data } = await invoicesApi.update(invoice.id, payload)
      onSaved(data)
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } }
      setError(ax?.response?.data?.detail || 'Erreur lors de l’enregistrement')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-base font-semibold text-gray-800">Modifier la facture</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-500">&times;</button>
        </div>
        <form onSubmit={submit} className="px-6 py-5 space-y-4">
          {error && (
            <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
          )}
          <p className="text-sm text-gray-500">
            Client : <span className="font-medium text-gray-800">{invoice.gestionnaire_name || '—'}</span>
          </p>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Formule</label>
            <input value={planName} onChange={e => setPlanName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Ex : Starter" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Montant (€)</label>
              <input type="number" min={0} step={0.01} value={amount} onChange={e => setAmount(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Statut</label>
              <select value={status} onChange={e => setStatus(e.target.value as 'paid' | 'unpaid')}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="unpaid">Impayée</option>
                <option value="paid">Payée</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Mois</label>
              <select value={month} onChange={e => setMonth(parseInt(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                {MONTHS.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Année</label>
              <input type="number" value={year} onChange={e => setYear(parseInt(e.target.value) || year)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">Annuler</button>
            <button type="submit" disabled={saving}
              className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 transition-colors">
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function InvoiceList() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1) // 1-12
  const [items, setItems] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [editing, setEditing] = useState<Invoice | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [sendingId, setSendingId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ kind: 'ok' | 'warn' | 'err'; msg: string } | null>(null)

  const load = useCallback(async (y: number, m: number) => {
    setLoading(true)
    try {
      const { data } = await invoicesApi.list(y, m)
      setItems(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(year, month) }, [year, month, load])

  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }

  const togglePaid = async (inv: Invoice) => {
    const next = inv.status === 'paid' ? 'unpaid' : 'paid'
    const { data } = await invoicesApi.update(inv.id, { status: next })
    setItems(prev => prev.map(i => (i.id === inv.id ? data : i)))
  }

  const remove = async (inv: Invoice) => {
    if (!confirm(`Supprimer définitivement la facture de ${inv.gestionnaire_name || 'ce client'} (${eur(inv.amount)}) ? Cette action est irréversible.`)) return
    await invoicesApi.remove(inv.id)
    setItems(prev => prev.filter(i => i.id !== inv.id))
  }

  const download = async (inv: Invoice) => {
    setDownloadingId(inv.id)
    try {
      const { data } = await invoicesApi.downloadPdf(inv.id)
      const url = window.URL.createObjectURL(data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `facture-${inv.period_year}-${String(inv.period_month).padStart(2, '0')}-${(inv.gestionnaire_name || 'client').replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } finally {
      setDownloadingId(null)
    }
  }

  const sendEmail = async (inv: Invoice) => {
    setSendingId(inv.id)
    try {
      const { data } = await invoicesApi.sendEmail(inv.id)
      if (data.sent) {
        setToast({ kind: 'ok', msg: `Facture envoyée à ${data.recipient}` })
      } else {
        setToast({ kind: 'warn', msg: data.detail || 'SMTP non configuré — envoi simulé.' })
      }
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } }
      setToast({ kind: 'err', msg: ax?.response?.data?.detail || 'Échec de l’envoi' })
    } finally {
      setSendingId(null)
      setTimeout(() => setToast(null), 5000)
    }
  }

  const regenerate = async () => {
    setGenerating(true)
    try {
      const { data } = await invoicesApi.generate(year, month)
      setItems(data)
    } finally {
      setGenerating(false)
    }
  }

  const onSaved = (inv: Invoice) => {
    // Si la période a changé, la facture sort de la vue courante
    if (inv.period_year !== year || inv.period_month !== month) {
      setItems(prev => prev.filter(i => i.id !== inv.id))
    } else {
      setItems(prev => prev.map(i => (i.id === inv.id ? inv : i)))
    }
    setEditing(null)
  }

  const total = items.reduce((s, i) => s + i.amount, 0)
  const paid = items.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0)
  const unpaid = total - paid

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <FileText size={24} className="text-gray-700" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Factures</h1>
            <p className="text-sm text-gray-500">Facturation mensuelle des gestionnaires</p>
          </div>
        </div>
        <button
          onClick={regenerate}
          disabled={generating}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition-colors"
        >
          <RefreshCw size={16} className={generating ? 'animate-spin' : ''} />
          Générer le mois
        </button>
      </div>

      {/* Sélecteur de période */}
      <div className="flex items-center justify-between gap-3 mb-5 bg-white rounded-xl border border-gray-200 px-3 py-2 max-w-sm">
        <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ChevronLeft size={18} />
        </button>
        <span className="text-sm font-semibold text-gray-800">{MONTHS[month - 1]} {year}</span>
        <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ChevronRight size={18} />
        </button>
      </div>

      {/* Synthèse */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Total facturé</p>
          <p className="text-xl font-bold text-gray-900 mt-1">{eur(total)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">Encaissé</p>
          <p className="text-xl font-bold text-emerald-600 mt-1">{eur(paid)}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-100 p-4">
          <p className="text-xs text-gray-500">En attente</p>
          <p className="text-xl font-bold text-amber-600 mt-1">{eur(unpaid)}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
        {loading ? (
          <div className="p-10 text-center text-gray-400 text-sm">Chargement…</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <FileText size={40} className="mx-auto mb-3 opacity-40" />
            <p className="font-medium">Aucune facture pour cette période</p>
            <p className="text-sm mt-1">Cliquez sur « Générer le mois » pour les créer.</p>
          </div>
        ) : (
          <table className="w-full text-sm min-w-[720px]">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Gestionnaire</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Formule</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-700">Montant</th>
                <th className="text-left px-4 py-3 font-semibold text-gray-700">Statut</th>
                <th className="text-right px-4 py-3 font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(inv => (
                <tr key={inv.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{inv.gestionnaire_name || '—'}</p>
                    <p className="text-xs text-gray-500">{inv.gestionnaire_email}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{inv.plan_name || '—'}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">{eur(inv.amount)}</td>
                  <td className="px-4 py-3">
                    {inv.status === 'paid' ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">Payée</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">Impayée</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => togglePaid(inv)}
                        title={inv.status === 'paid' ? 'Marquer impayée' : 'Marquer payée'}
                        className={`p-2 rounded-lg transition-colors ${
                          inv.status === 'paid'
                            ? 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
                            : 'text-green-600 hover:bg-green-50'
                        }`}
                      >
                        {inv.status === 'paid' ? <RotateCw size={16} /> : <Check size={16} />}
                      </button>
                      <button
                        onClick={() => download(inv)}
                        disabled={downloadingId === inv.id}
                        title="Télécharger le PDF"
                        className="p-2 rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors disabled:opacity-50"
                      >
                        <Download size={16} className={downloadingId === inv.id ? 'animate-pulse' : ''} />
                      </button>
                      <button
                        onClick={() => sendEmail(inv)}
                        disabled={sendingId === inv.id}
                        title="Envoyer par email"
                        className="p-2 rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors disabled:opacity-50"
                      >
                        <Mail size={16} className={sendingId === inv.id ? 'animate-pulse' : ''} />
                      </button>
                      <button
                        onClick={() => setEditing(inv)}
                        title="Modifier"
                        className="p-2 rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        onClick={() => remove(inv)}
                        title="Supprimer"
                        className="p-2 rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {editing && (
        <EditModal invoice={editing} onClose={() => setEditing(null)} onSaved={onSaved} />
      )}

      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 max-w-sm px-4 py-3 rounded-xl shadow-lg text-sm border ${
            toast.kind === 'ok'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : toast.kind === 'warn'
                ? 'bg-amber-50 border-amber-200 text-amber-800'
                : 'bg-red-50 border-red-200 text-red-800'
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  )
}
