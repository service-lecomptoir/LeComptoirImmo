import { useState, useEffect, useCallback } from 'react'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'
import { formatEuro as fmtEuro } from '@/utils/format'
import { coproApi, type CoproAccount } from '@/api/coproprietes'

export function CoproAccountsTab({ coproId }: { coproId: string }) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [rows, setRows] = useState<CoproAccount[]>([])
  const [loading, setLoading] = useState(true)
  const years = [now.getFullYear() + 1, now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2]

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await coproApi.accounts(coproId, year)
      setRows(data)
    } catch (e) {
      toast.error(getErrorMessage(e, 'Erreur lors du chargement des comptes'))
    } finally { setLoading(false) }
  }, [coproId, year])

  useEffect(() => { load() }, [load])

  const totals = rows.reduce(
    (s, r) => ({ due: s.due + r.total_due, paid: s.paid + r.total_paid, bal: s.bal + r.balance }),
    { due: 0, paid: 0, bal: 0 },
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <label className="text-sm text-gray-600">Année</label>
        <select value={year} onChange={e => setYear(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
          {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <p className="px-4 py-6 text-sm text-gray-400">Chargement…</p>
        ) : rows.length === 0 ? (
          <p className="px-4 py-6 text-sm text-gray-400">Aucun appel de fonds sur {year}.</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-gray-500 uppercase">
              <th className="px-4 py-2">Copropriétaire</th>
              <th className="px-4 py-2 text-right">Appelé</th>
              <th className="px-4 py-2 text-right">Payé</th>
              <th className="px-4 py-2 text-right">Solde</th>
            </tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.owner_id ?? i} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-medium text-gray-900">{r.owner_name}</td>
                  <td className="px-4 py-2 text-right">{fmtEuro(r.total_due)}</td>
                  <td className="px-4 py-2 text-right text-green-700">{fmtEuro(r.total_paid)}</td>
                  <td className={`px-4 py-2 text-right font-medium ${r.balance > 0 ? 'text-amber-700' : 'text-green-700'}`}>{fmtEuro(r.balance)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-gray-200 bg-gray-50 font-medium">
                <td className="px-4 py-2">Total</td>
                <td className="px-4 py-2 text-right">{fmtEuro(totals.due)}</td>
                <td className="px-4 py-2 text-right text-green-700">{fmtEuro(totals.paid)}</td>
                <td className={`px-4 py-2 text-right ${totals.bal > 0 ? 'text-amber-700' : 'text-green-700'}`}>{fmtEuro(totals.bal)}</td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>
    </div>
  )
}
