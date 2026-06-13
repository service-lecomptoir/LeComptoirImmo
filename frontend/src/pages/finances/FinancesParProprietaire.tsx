import { useState, useEffect } from 'react'
import { ChevronRight, ChevronDown, FileDown, RefreshCw, KeyRound, Wallet } from 'lucide-react'
import { ownersApi, type OwnerFinances } from '@/api/owners'
import type { OwnerListItem } from '@/types/owner'
import { docFilename } from '@/utils/filename'
import { StatusBadge } from '@/components/common/StatusBadge'
import { PAYMENT_STATUS_LABELS, PAYMENT_STATUS_VARIANTS } from '@/types/payment'
import type { PaymentStatus } from '@/types/payment'

type View = 'revenus' | 'biens' | 'fiscal'

const fmtEuro = (n: number) =>
  (n ?? 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

// Statuts spécifiques aux lignes d'apurement (hors énumération paiement standard).
const EXTRA_STATUS: Record<string, { label: string; variant: any }> = {
  reporte: { label: 'Reporté (apurement)', variant: 'blue' },
  apurement: { label: 'Apurement', variant: 'green' },
}
const statusLabel = (s: string) => EXTRA_STATUS[s]?.label ?? PAYMENT_STATUS_LABELS[s as PaymentStatus] ?? s
const statusVariant = (s: string) => EXTRA_STATUS[s]?.variant ?? PAYMENT_STATUS_VARIANTS[s as PaymentStatus] ?? 'gray'

const META: Record<View, { title: string; subtitle: string }> = {
  revenus: { title: 'Revenus par propriétaire', subtitle: 'Loyers appelés et encaissés, par bailleur' },
  biens: { title: 'Performance des biens', subtitle: 'Rendement et encaissements par bien, par bailleur' },
  fiscal: { title: 'Liasse fiscale par propriétaire', subtitle: 'Synthèse des revenus fonciers, imprimable par bailleur' },
}

export default function FinancesParProprietaire({ view }: { view: View }) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [owners, setOwners] = useState<OwnerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [data, setData] = useState<Record<string, OwnerFinances>>({})
  const [fetchingId, setFetchingId] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  useEffect(() => {
    ownersApi.list({ limit: 200 })
      .then(r => setOwners(r.data.items))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { setData({}); setExpandedId(null) }, [year])

  const toggle = async (o: OwnerListItem) => {
    if (expandedId === o.id) { setExpandedId(null); return }
    setExpandedId(o.id)
    const key = `${o.id}:${year}`
    if (!data[key]) {
      setFetchingId(o.id)
      try {
        const r = await ownersApi.finances(o.id, year)
        setData(prev => ({ ...prev, [key]: r.data }))
      } catch { /* ignore */ } finally { setFetchingId(null) }
    }
  }

  const downloadFiscal = async (o: OwnerListItem) => {
    setDownloadingId(o.id)
    try {
      await ownersApi.fiscalPdf(o.id, year, docFilename('liasse_fiscale', { tenant: o.full_name, year }))
    } finally { setDownloadingId(null) }
  }

  const meta = META[view]
  const years = [now.getFullYear() + 1, now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2]

  const renderDetail = (fin: OwnerFinances) => {
    if (view === 'revenus') {
      return (
        <>
          <div className="flex flex-wrap gap-4 mb-3 text-sm">
            <span className="text-gray-500">Total appelé : <strong className="text-gray-900">{fmtEuro(fin.revenus.total_du)}</strong></span>
            <span className="text-gray-500">Total encaissé : <strong className="text-green-700">{fmtEuro(fin.revenus.total_percu)}</strong></span>
          </div>
          {fin.revenus.lignes.length === 0 ? (
            <p className="text-sm text-gray-400">Aucun loyer sur {fin.year}.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead><tr className="text-left text-xs text-gray-500 uppercase">
                  <th className="px-3 py-2">Période</th><th className="px-3 py-2">Bien</th>
                  <th className="px-3 py-2">Locataire</th>
                  <th className="px-3 py-2 text-right">Appelé</th><th className="px-3 py-2 text-right">Encaissé</th>
                  <th className="px-3 py-2">Statut</th>
                </tr></thead>
                <tbody>
                  {fin.revenus.lignes.map((l, i) => (
                    <tr key={i} className="border-t border-gray-100">
                      <td className="px-3 py-2">{l.period_label}</td>
                      <td className="px-3 py-2">{l.property_name}</td>
                      <td className="px-3 py-2">{l.tenant_full_name}</td>
                      <td className="px-3 py-2 text-right">{fmtEuro(l.amount_due)}</td>
                      <td className="px-3 py-2 text-right text-green-700">{fmtEuro(l.amount_paid)}</td>
                      <td className="px-3 py-2"><StatusBadge label={statusLabel(l.status)} variant={statusVariant(l.status)} dot /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )
    }
    if (view === 'biens') {
      return fin.biens.length === 0 ? (
        <p className="text-sm text-gray-400">Aucun bien rattaché.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead><tr className="text-left text-xs text-gray-500 uppercase">
              <th className="px-3 py-2">Bien</th><th className="px-3 py-2 text-right">Loyer + charges /mois</th>
              <th className="px-3 py-2 text-right">Appelé {fin.year}</th><th className="px-3 py-2 text-right">Encaissé {fin.year}</th>
              <th className="px-3 py-2">Occupation</th>
            </tr></thead>
            <tbody>
              {fin.biens.map(b => (
                <tr key={b.property_id} className="border-t border-gray-100">
                  <td className="px-3 py-2">{b.property_name}</td>
                  <td className="px-3 py-2 text-right">{fmtEuro(b.rent + b.charges)}</td>
                  <td className="px-3 py-2 text-right">{fmtEuro(b.total_du)}</td>
                  <td className="px-3 py-2 text-right text-green-700">{fmtEuro(b.total_percu)}</td>
                  <td className="px-3 py-2">{b.is_occupied
                    ? <span className="text-xs text-green-700 bg-green-50 rounded-full px-2 py-0.5">Loué</span>
                    : <span className="text-xs text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">Vacant</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    // fiscal — format 2044 simplifié (mêmes sections que la page GP)
    const f = fin.fiscal
    const net = f.net_revenue
    const row = (label: string, sub: string, value: number, strong = false) => (
      <div className={`flex justify-between items-start gap-4 px-3 py-2 ${strong ? 'bg-gray-50 font-semibold' : 'border-b border-gray-100'}`}>
        <div><p className="text-sm text-gray-900">{label}</p>{sub && <p className="text-[11px] text-gray-400">{sub}</p>}</div>
        <p className="text-sm text-gray-900 whitespace-nowrap">{fmtEuro(value)}</p>
      </div>
    )
    return (
      <div className="max-w-xl space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div className="bg-blue-50 rounded-lg p-2 text-center"><p className="text-base font-bold text-blue-700">{fmtEuro(f.total_gross_revenue)}</p><p className="text-[11px] text-blue-600">Revenus bruts</p></div>
          <div className="bg-orange-50 rounded-lg p-2 text-center"><p className="text-base font-bold text-orange-700">{fmtEuro(f.total_deductible)}</p><p className="text-[11px] text-orange-600">Charges déductibles</p></div>
          <div className={`${net >= 0 ? 'bg-green-50' : 'bg-red-50'} rounded-lg p-2 text-center`}><p className={`text-base font-bold ${net >= 0 ? 'text-green-700' : 'text-red-700'}`}>{fmtEuro(net)}</p><p className={`text-[11px] ${net >= 0 ? 'text-green-600' : 'text-red-600'}`}>{net >= 0 ? 'Revenu net imposable' : 'Déficit foncier'}</p></div>
        </div>

        <div className="rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-gray-800 text-white px-3 py-1.5 text-xs font-semibold">SECTION A : REVENUS BRUTS</div>
          {row('Loyers encaissés', 'Ligne 100 : Recettes brutes', f.gross_rent_revenue)}
          {row('Provisions pour charges récupérées', 'Ligne 110 : Charges locatives', f.charges_received)}
          {row('Total revenus bruts (A)', '', f.total_gross_revenue, true)}
        </div>

        <div className="rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-gray-800 text-white px-3 py-1.5 text-xs font-semibold">SECTION B : CHARGES DÉDUCTIBLES</div>
          {row("Frais de gestion et d'administration", 'Ligne 120 : 8% des loyers bruts (estimation)', f.management_fees)}
          {row('Total charges déductibles (B)', '', f.total_deductible, true)}
        </div>

        <div className={`rounded-lg border overflow-hidden ${net >= 0 ? 'border-green-200' : 'border-red-200'}`}>
          <div className={`px-3 py-1.5 text-xs font-semibold text-white ${net >= 0 ? 'bg-green-700' : 'bg-red-700'}`}>SECTION C : RÉSULTAT FISCAL</div>
          <div className={`flex justify-between items-center gap-4 px-3 py-2 ${net >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <div><p className="text-sm font-bold text-gray-900">{net >= 0 ? 'Revenu foncier net imposable' : 'Déficit foncier'}</p><p className="text-[11px] text-gray-500">A − B = à reporter sur la déclaration 2042</p></div>
            <p className={`text-lg font-bold ${net >= 0 ? 'text-green-700' : 'text-red-700'}`}>{fmtEuro(Math.abs(net))}</p>
          </div>
        </div>

        <button
          onClick={() => downloadFiscal({ id: fin.owner_id, full_name: fin.owner_name } as OwnerListItem)}
          disabled={downloadingId === fin.owner_id}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {downloadingId === fin.owner_id ? <RefreshCw size={14} className="animate-spin" /> : <FileDown size={14} />}
          Télécharger la liasse fiscale (PDF)
        </button>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{meta.title}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{meta.subtitle}</p>
        </div>
        <select
          value={year}
          onChange={e => setYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-fit"
        >
          {years.map(y => <option key={y} value={y}>Année {y}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-gray-400">Chargement…</div>
        ) : owners.length === 0 ? (
          <div className="p-12 text-center text-gray-400">
            <Wallet size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">Aucun propriétaire.</p>
          </div>
        ) : (
          owners.map(o => {
            const fin = data[`${o.id}:${year}`]
            const open = expandedId === o.id
            return (
              <div key={o.id} className="border-b border-gray-100 last:border-0">
                <button
                  onClick={() => toggle(o)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50"
                >
                  {open ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
                  <span className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                    <KeyRound size={15} className="text-blue-600" />
                  </span>
                  <span className="text-sm font-medium text-gray-900 flex-1">{o.full_name}</span>
                  {fin && view !== 'biens' && (
                    <span className="text-xs text-gray-500 whitespace-nowrap">Encaissé {year} : <strong className="text-green-700">{fmtEuro(fin.revenus.total_percu)}</strong></span>
                  )}
                </button>
                {open && (
                  <div className="px-4 pb-4 pt-1 bg-blue-50/30">
                    {fetchingId === o.id || !fin
                      ? <p className="text-sm text-gray-400 py-2">Chargement des données…</p>
                      : renderDetail(fin)}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
