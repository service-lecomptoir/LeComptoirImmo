import { useState, useEffect, useCallback } from 'react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import {
  Calendar, Plus, Download, Send, CheckCircle,
  Trash2, RefreshCw, Filter,
} from 'lucide-react'
import { avisEcheancesApi, type AvisEcheanceSummary } from '@/api/avis_echeances'
import { leasesApi } from '@/api/leases'
import { useAuthStore } from '@/store/authStore'
import { StatusBadge } from '@/components/common/StatusBadge'

const MONTHS = [
  '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

function statusVariant(s: string): 'gray' | 'blue' | 'green' {
  if (s === 'envoye') return 'blue'
  if (s === 'acquitte') return 'green'
  return 'gray'
}
function statusLabel(s: string): string {
  if (s === 'envoye') return 'Envoyé'
  if (s === 'acquitte') return 'Acquitté'
  return 'Brouillon'
}

// ── Modale génération manuelle ────────────────────────────────────────────────
function GenerateModal({
  onClose,
  onGenerated,
}: {
  onClose: () => void
  onGenerated: () => void
}) {
  const now = new Date()
  const [leaseId, setLeaseId] = useState('')
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [leases, setLeases] = useState<{ id: string; label: string }[]>([])

  useEffect(() => {
    leasesApi.list({ is_active: true, limit: 200 }).then(r => {
      setLeases(
        r.data.items.map((l: any) => ({
          id: l.id,
          label: `${l.tenant_full_name} — ${l.property_name} ${l.unit_ref}`,
        }))
      )
    })
  }, [])

  const handleSubmit = async () => {
    if (!leaseId) { setError('Sélectionnez un bail'); return }
    setLoading(true); setError('')
    try {
      await avisEcheancesApi.generate({ lease_id: leaseId, period_year: year, period_month: month })
      onGenerated()
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Erreur lors de la génération')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Calendar size={18} className="text-blue-600" />
          Générer un avis d'échéance
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Bail</label>
            <select
              value={leaseId}
              onChange={e => setLeaseId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">— Sélectionner un bail —</option>
              {leases.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Mois</label>
              <select
                value={month}
                onChange={e => setMonth(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {MONTHS.slice(1).map((m, i) => (
                  <option key={i + 1} value={i + 1}>{m}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Année</label>
              <input
                type="number"
                value={year}
                onChange={e => setYear(Number(e.target.value))}
                min={2020}
                max={2035}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Génération…' : 'Générer'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Modale génération mensuelle ───────────────────────────────────────────────
function BulkGenerateModal({
  onClose,
  onGenerated,
}: {
  onClose: () => void
  onGenerated: (msg: string) => void
}) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setLoading(true); setError('')
    try {
      const r = await avisEcheancesApi.generateMonthly({ period_year: year, period_month: month })
      onGenerated(r.data.message)
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Erreur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
        <h2 className="text-lg font-bold text-gray-900 mb-2 flex items-center gap-2">
          <RefreshCw size={18} className="text-purple-600" />
          Génération automatique du mois
        </h2>
        <p className="text-sm text-gray-500 mb-4">
          Génère les avis pour tous les baux actifs n'ayant pas encore d'avis pour la période.
        </p>

        <div className="flex gap-3 mb-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Mois</label>
            <select
              value={month}
              onChange={e => setMonth(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {MONTHS.slice(1).map((m, i) => (
                <option key={i + 1} value={i + 1}>{m}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Année</label>
            <input
              type="number"
              value={year}
              onChange={e => setYear(Number(e.target.value))}
              min={2020}
              max={2035}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3">{error}</p>}

        <div className="flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-gray-300 text-sm text-gray-700 hover:bg-gray-50">
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          >
            {loading ? 'Génération…' : 'Générer tous'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function AvisEcheanceList() {
  const { user } = useAuthStore()
  const isManager = user?.role === 'admin' || user?.role === 'gestionnaire'

  const now = new Date()
  const [filterYear, setFilterYear] = useState<number>(now.getFullYear())
  const [filterMonth, setFilterMonth] = useState<number>(0) // 0 = tous
  const [filterStatus, setFilterStatus] = useState('')
  const [avis, setAvis] = useState<AvisEcheanceSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [successMsg, setSuccessMsg] = useState('')

  const [showGenerate, setShowGenerate] = useState(false)
  const [showBulk, setShowBulk] = useState(false)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const r = await avisEcheancesApi.list({
        year: filterYear || undefined,
        month: filterMonth || undefined,
        status: filterStatus || undefined,
        limit: 100,
      })
      setAvis(r.data)
    } catch { /* ignore */ } finally {
      setIsLoading(false)
    }
  }, [filterYear, filterMonth, filterStatus])

  useEffect(() => { load() }, [load])

  const handleMarkSent = async (id: string) => {
    await avisEcheancesApi.markSent(id)
    setSuccessMsg('Avis marqué comme envoyé')
    setTimeout(() => setSuccessMsg(''), 3000)
    load()
  }

  const handleMarkAcquitte = async (id: string) => {
    await avisEcheancesApi.markAcquitte(id)
    setSuccessMsg('Avis marqué comme acquitté')
    setTimeout(() => setSuccessMsg(''), 3000)
    load()
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Supprimer cet avis ?')) return
    await avisEcheancesApi.delete(id)
    load()
  }

  const downloadPdf = (id: string, label: string) => {
    const token = localStorage.getItem('access_token')
    const url = avisEcheancesApi.pdfUrl(id)
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `avis-${label}.pdf`
        a.click()
      })
  }

  const years = Array.from({ length: 6 }, (_, i) => now.getFullYear() - 2 + i)

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Avis d'échéances</h1>
          <p className="text-gray-500 text-sm mt-1">Appels de loyer mensuels</p>
        </div>
        {isManager && (
          <div className="flex gap-2">
            <button
              onClick={() => setShowBulk(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-purple-200 bg-purple-50 text-purple-700 text-sm font-medium hover:bg-purple-100 transition-colors"
            >
              <RefreshCw size={15} />
              Génération mensuelle
            </button>
            <button
              onClick={() => setShowGenerate(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <Plus size={15} />
              Générer un avis
            </button>
          </div>
        )}
      </div>

      {successMsg && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-green-50 text-green-800 text-sm border border-green-200">
          {successMsg}
        </div>
      )}

      {/* Filtres */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-5 flex flex-wrap gap-3 items-center">
        <Filter size={15} className="text-gray-400" />
        <select
          value={filterYear}
          onChange={e => setFilterYear(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select
          value={filterMonth}
          onChange={e => setFilterMonth(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={0}>Tous les mois</option>
          {MONTHS.slice(1).map((m, i) => (
            <option key={i + 1} value={i + 1}>{m}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Tous les statuts</option>
          <option value="brouillon">Brouillon</option>
          <option value="envoye">Envoyé</option>
          <option value="acquitte">Acquitté</option>
        </select>
        <button onClick={load} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
          <RefreshCw size={12} /> Actualiser
        </button>
        <span className="ml-auto text-xs text-gray-400">{avis.length} avis</span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-gray-400 text-sm">Chargement…</div>
        ) : avis.length === 0 ? (
          <div className="py-16 text-center text-gray-400">
            <Calendar size={32} className="mx-auto mb-3 text-gray-300" />
            <p className="text-sm font-medium">Aucun avis d'échéance</p>
            {isManager && (
              <p className="text-xs mt-1">
                Utilisez le bouton « Génération mensuelle » pour créer tous les avis du mois.
              </p>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Période</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire / Logement</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Montant</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Échéance</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Statut</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {avis.map(a => (
                <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{a.period_label}</p>
                    {a.is_auto_generated && (
                      <span className="text-xs text-gray-400">auto</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{a.tenant_full_name}</p>
                    <p className="text-xs text-gray-500">{a.unit_ref}</p>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <p className="text-sm font-semibold text-gray-900">{fmtEuro(a.amount_total)}</p>
                    {a.amount_apl && (
                      <p className="text-xs text-green-600">APL -{fmtEuro(a.amount_apl)}</p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-700">
                      {format(new Date(a.due_date), 'd MMM yyyy', { locale: fr })}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge label={statusLabel(a.status)} variant={statusVariant(a.status)} dot />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {/* PDF */}
                      <button
                        onClick={() => downloadPdf(a.id, `${a.period_label}-${a.tenant_full_name}`)}
                        title="Télécharger PDF"
                        className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-blue-600"
                      >
                        <Download size={14} />
                      </button>

                      {isManager && (
                        <>
                          {a.status === 'brouillon' && (
                            <button
                              onClick={() => handleMarkSent(a.id)}
                              title="Marquer comme envoyé"
                              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-blue-600"
                            >
                              <Send size={14} />
                            </button>
                          )}
                          {a.status !== 'acquitte' && (
                            <button
                              onClick={() => handleMarkAcquitte(a.id)}
                              title="Marquer comme acquitté"
                              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-green-600"
                            >
                              <CheckCircle size={14} />
                            </button>
                          )}
                          {a.status === 'brouillon' && (
                            <button
                              onClick={() => handleDelete(a.id)}
                              title="Supprimer"
                              className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-red-600"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modales */}
      {showGenerate && (
        <GenerateModal
          onClose={() => setShowGenerate(false)}
          onGenerated={() => { load(); setSuccessMsg('Avis généré avec succès') }}
        />
      )}
      {showBulk && (
        <BulkGenerateModal
          onClose={() => setShowBulk(false)}
          onGenerated={(msg) => { load(); setSuccessMsg(msg) }}
        />
      )}
    </div>
  )
}
