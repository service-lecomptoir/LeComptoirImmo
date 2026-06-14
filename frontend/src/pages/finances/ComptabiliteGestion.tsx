import { useState, useEffect, useMemo } from 'react'
import { BookText, Download, Search } from 'lucide-react'
import { apiClient } from '@/api/client'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

const fmtEuro = (n: number) =>
  n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €'

interface Entry {
  date: string | null
  logement: string
  logement_ref: string
  proprietaire: string
  locataire: string
  intitule: string
  montant: number
  sign: 'debit' | 'credit'
}

/** Tableau de grand livre (colonnes : Date, Logement, [Propriétaire], Locataire, Intitulé, Montant). */
function LedgerTable({ items, showOwner }: { items: Entry[]; showOwner: boolean }) {
  const cols = showOwner ? 6 : 5
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px]">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Logement</th>
            {showOwner && <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Propriétaire</th>}
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Intitulé</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Montant</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.length === 0 ? (
            <tr><td colSpan={cols} className="px-4 py-6 text-center text-sm text-gray-400">Aucune transaction</td></tr>
          ) : items.map((e, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                {e.date ? format(new Date(e.date), 'd MMM yyyy', { locale: fr }) : '·'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-800">
                {e.logement}
                {e.logement_ref && <span className="ml-1 text-xs text-gray-400 font-mono">{e.logement_ref}</span>}
              </td>
              {showOwner && <td className="px-4 py-3 text-sm text-gray-600">{e.proprietaire || '·'}</td>}
              <td className="px-4 py-3 text-sm text-gray-600">{e.locataire || '·'}</td>
              <td className="px-4 py-3 text-sm text-gray-800">{e.intitule}</td>
              <td className={`px-4 py-3 text-right text-sm font-medium whitespace-nowrap ${e.sign === 'credit' ? 'text-green-600' : 'text-red-600'}`}>
                {e.sign === 'credit' ? `+ ${fmtEuro(e.montant)}` : `− ${fmtEuro(e.montant)}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const groupNet = (items: Entry[]) => {
  const d = items.filter(e => e.sign === 'debit').reduce((s, e) => s + e.montant, 0)
  const c = items.filter(e => e.sign === 'credit').reduce((s, e) => s + e.montant, 0)
  return Math.round((d - c) * 100) / 100
}

export default function ComptabiliteGestion() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [isMandataire, setIsMandataire] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [q, setQ] = useState('')

  useEffect(() => {
    apiClient.get('/payments/comptabilite')
      .then(({ data }) => { setEntries(data.entries ?? []); setIsMandataire(!!data.is_mandataire) })
      .catch(() => { /* l'intercepteur gère le toast */ })
      .finally(() => setIsLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase()
    if (!t) return entries
    return entries.filter(e =>
      [e.logement, e.logement_ref, e.proprietaire, e.locataire, e.intitule]
        .some(v => (v || '').toLowerCase().includes(t)))
  }, [entries, q])

  const totalDebits = filtered.filter(e => e.sign === 'debit').reduce((s, e) => s + e.montant, 0)
  const totalCredits = filtered.filter(e => e.sign === 'credit').reduce((s, e) => s + e.montant, 0)
  const solde = Math.round((totalDebits - totalCredits) * 100) / 100

  // Mandataire : regroupement des écritures par propriétaire (sections + sous-total).
  const groups = useMemo(() => {
    if (!isMandataire) return null
    const m = new Map<string, Entry[]>()
    for (const e of filtered) {
      const k = e.proprietaire || '(Sans propriétaire)'
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(e)
    }
    return Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  }, [filtered, isMandataire])

  const handleExport = () => {
    const sep = ';'
    const esc = (s: string) => `"${(s || '').replace(/"/g, '""')}"`
    const head = ['Date', 'Logement', ...(isMandataire ? ['Propriétaire'] : []), 'Locataire', 'Intitulé', 'Montant']
    const lines = filtered.map(e => [
      e.date ? format(new Date(e.date), 'dd/MM/yyyy') : '',
      esc(e.logement_ref ? `${e.logement} (${e.logement_ref})` : e.logement),
      ...(isMandataire ? [esc(e.proprietaire)] : []),
      esc(e.locataire),
      esc(e.intitule),
      (e.sign === 'credit' ? '' : '-') + e.montant.toFixed(2).replace('.', ','),
    ].join(sep))
    const csv = String.fromCharCode(0xFEFF) + [head.join(sep), ...lines].join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'comptabilite.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-6 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BookText size={22} className="text-[#0D2F5C]" /> Comptabilité
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Grand livre de toutes les transactions : appels de loyer, règlements, apurement, régularisations de charges.
          </p>
        </div>
        {filtered.length > 0 && (
          <button onClick={handleExport}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium text-white flex-shrink-0"
            style={{ background: '#0D2F5C' }}>
            <Download size={15} /> Exporter
          </button>
        )}
      </div>

      {/* Solde net + recherche */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <div className="rounded-xl border border-gray-200 bg-white px-4 py-2.5">
          <span className="text-xs uppercase tracking-wide font-medium text-gray-500">Solde net</span>
          <span className={`ml-2 text-lg font-bold ${solde > 0.005 ? 'text-red-600' : solde < -0.005 ? 'text-green-600' : 'text-gray-700'}`}>
            {solde > 0.005 ? `− ${fmtEuro(solde)}` : solde < -0.005 ? `+ ${fmtEuro(-solde)}` : '0,00 €'}
          </span>
        </div>
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={q} onChange={e => setQ(e.target.value)}
            placeholder={isMandataire ? 'Rechercher (logement, propriétaire, locataire…)' : 'Rechercher (logement, locataire…)'}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 py-12 text-center text-gray-400 text-sm">Chargement…</div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 py-12 text-center text-gray-400">
          <BookText size={32} className="mx-auto mb-2 text-gray-300" />
          <p className="text-sm">Aucune transaction</p>
        </div>
      ) : groups ? (
        // Mandataire : une section par propriétaire, avec sous-total net.
        <div className="space-y-5">
          {groups.map(([owner, items]) => {
            const net = groupNet(items)
            return (
              <div key={owner} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between gap-3 px-4 py-3 bg-gray-50 border-b border-gray-200">
                  <h2 className="text-sm font-bold text-gray-900">Propriétaire : {owner}</h2>
                  <span className="text-sm">
                    <span className="text-xs uppercase tracking-wide text-gray-500 mr-2">Solde net</span>
                    <span className={`font-bold ${net > 0.005 ? 'text-red-600' : net < -0.005 ? 'text-green-600' : 'text-gray-700'}`}>
                      {net > 0.005 ? `− ${fmtEuro(net)}` : net < -0.005 ? `+ ${fmtEuro(-net)}` : '0,00 €'}
                    </span>
                  </span>
                </div>
                <LedgerTable items={items} showOwner={false} />
              </div>
            )
          })}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <LedgerTable items={filtered} showOwner={false} />
        </div>
      )}
    </div>
  )
}
