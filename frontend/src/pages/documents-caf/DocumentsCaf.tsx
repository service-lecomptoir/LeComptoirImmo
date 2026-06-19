import { useEffect, useMemo, useState } from 'react'
import { Landmark, Search, Loader2, CalendarClock, ExternalLink, ChevronRight, ChevronDown, KeyRound, Send, Inbox, Eye } from 'lucide-react'
import { leasesApi } from '@/api/leases'
import type { LeaseListItem } from '@/types/lease'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'
import { cafApi, type CafDocType } from '@/api/caf'
import { getErrorMessage } from '@/utils/errors'

const CAF_PARTENAIRES_URL = 'https://partenaires.caf.fr/cnafappli/authentificationpartenaireappli/dist/#/connexion'

export default function DocumentsCaf() {
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const declarationPeriod = new Date().getMonth() >= 6
  const isMandataire = useAuthStore(s => s.user?.role === 'gestionnaire')
  const [collapsedOwners, setCollapsedOwners] = useState<Set<string>>(new Set())
  const toggleOwner = (owner: string) =>
    setCollapsedOwners(prev => {
      const next = new Set(prev)
      next.has(owner) ? next.delete(owner) : next.add(owner)
      return next
    })

  useEffect(() => {
    leasesApi.list({ is_active: true, limit: 200 })
      .then(r => setLeases(r.data.items ?? []))
      .catch(() => toast.error('Chargement des contrats impossible'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return leases
    return leases.filter(l =>
      l.tenant_full_name?.toLowerCase().includes(q) ||
      l.property_name?.toLowerCase().includes(q)
    )
  }, [leases, search])

  const openDoc = async (lease: LeaseListItem, dt: CafDocType) => {
    setBusy(`${lease.id}:${dt}:view`)
    try {
      const r = await cafApi.openPdf(lease.id, dt)
      const url = URL.createObjectURL(r.data as Blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) { toast.error(getErrorMessage(e, 'Génération impossible')) }
    finally { setBusy(null) }
  }
  const emailDoc = async (lease: LeaseListItem, dt: CafDocType) => {
    setBusy(`${lease.id}:${dt}:mail`)
    try {
      const r = await cafApi.email(lease.id, dt)
      toast.success(r.data.email_sent ? 'Document envoyé au locataire.' : 'E-mail non envoyé (SMTP indisponible ou pas d\'adresse).')
    } catch (e) { toast.error(getErrorMessage(e, 'Envoi impossible')) }
    finally { setBusy(null) }
  }
  const depositDoc = async (lease: LeaseListItem, dt: CafDocType) => {
    setBusy(`${lease.id}:${dt}:dep`)
    try {
      await cafApi.deposit(lease.id, dt)
      toast.success('Document déposé dans l\'espace du locataire.')
    } catch (e) { toast.error(getErrorMessage(e, 'Dépôt impossible')) }
    finally { setBusy(null) }
  }

  const ownerGroups: [string, LeaseListItem[]][] = (() => {
    const acc: Record<string, LeaseListItem[]> = {}
    for (const l of filtered) {
      const key = l.owner_name || 'Sans propriétaire'
      ;(acc[key] ||= []).push(l)
    }
    return Object.entries(acc).sort((a, b) => a[0].localeCompare(b[0], 'fr'))
  })()

  const docActions = (l: LeaseListItem, dt: CafDocType, label: string) => (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[11px] text-gray-400">{label}</span>
      <div className="inline-flex items-center gap-1">
        <button onClick={() => openDoc(l, dt)} disabled={busy === `${l.id}:${dt}:view`} title="Générer / Voir"
          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-60">
          {busy === `${l.id}:${dt}:view` ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />} Voir
        </button>
        <button onClick={() => emailDoc(l, dt)} disabled={busy === `${l.id}:${dt}:mail`} title="Envoyer au locataire"
          className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-60">
          {busy === `${l.id}:${dt}:mail` ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
        </button>
        <button onClick={() => depositDoc(l, dt)} disabled={busy === `${l.id}:${dt}:dep`} title="Déposer dans l'espace locataire"
          className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-60">
          {busy === `${l.id}:${dt}:dep` ? <Loader2 size={13} className="animate-spin" /> : <Inbox size={13} />}
        </button>
      </div>
    </div>
  )

  const renderRow = (l: LeaseListItem) => (
    <tr key={l.id} className="hover:bg-blue-50/40 transition-colors">
      <td className="px-6 py-4 text-sm font-medium text-gray-900 text-center">{l.tenant_full_name}</td>
      <td className="px-6 py-4 text-sm text-gray-600 text-center">{l.property_name}</td>
      <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap text-center">
        {l.start_date ? new Date(l.start_date).toLocaleDateString('fr-FR') : '-'}
      </td>
      <td className="px-6 py-4">
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          {docActions(l, 'attestation', 'Attestation de loyer')}
          {docActions(l, 'tiers_payant', 'Formulaire tiers payant')}
        </div>
      </td>
    </tr>
  )

  const renderTable = (items: LeaseListItem[]) => (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
      <table className="w-full min-w-[680px]">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50">
            <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire</th>
            <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Bien</th>
            <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Depuis le</th>
            <th className="px-6 py-3.5 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide">Documents</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">{items.map(renderRow)}</tbody>
      </table>
    </div>
  )

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
          <Landmark className="text-blue-600" size={20} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Espace CAF</h1>
          <p className="text-gray-500 text-sm">Attestation de loyer et formulaire tiers payant : remplis, signés, à envoyer ou déposer</p>
        </div>
      </div>

      {declarationPeriod ? (
        <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <CalendarClock size={18} className="mt-0.5 shrink-0 text-amber-600" />
          <div>
            <span className="font-semibold">La déclaration de loyers à la CAF est ouverte (juillet → décembre).</span>{' '}
            Déclarez les loyers de chaque locataire bénéficiaire sur la plateforme partenaires de la CAF.
            <a href={CAF_PARTENAIRES_URL} target="_blank" rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1.5 font-semibold text-amber-900 underline hover:text-amber-700">
              Accéder à la plateforme partenaires CAF <ExternalLink size={14} />
            </a>
          </div>
        </div>
      ) : (
        <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
          <CalendarClock size={18} className="mt-0.5 shrink-0 text-gray-400" />
          <div>La déclaration de loyers n'est pas ouverte actuellement (elle a lieu de juillet à décembre).</div>
        </div>
      )}

      <p className="text-sm text-gray-500 mb-6 max-w-2xl">
        Sélectionnez un contrat : l'attestation de loyer et le formulaire tiers payant sont pré-remplis à
        partir des informations du bailleur, du locataire et du bail, et signés. Vous pouvez les consulter,
        les envoyer au locataire ou les déposer dans son espace.
      </p>

      <div className="relative mb-5 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher par locataire ou bien…"
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-200" />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16"><Loader2 className="animate-spin text-blue-600" size={28} /></div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 px-6 py-12 text-center text-sm text-gray-400">
          {search ? 'Aucun contrat ne correspond à votre recherche' : 'Aucun contrat actif'}
        </div>
      ) : isMandataire ? (
        <div className="space-y-4">
          {ownerGroups.map(([owner, items]) => {
            const open = !collapsedOwners.has(owner)
            return (
              <div key={owner}>
                <button onClick={() => toggleOwner(owner)} className="w-full flex items-center gap-2 mb-2 text-left">
                  {open ? <ChevronDown size={15} className="text-gray-400 shrink-0" /> : <ChevronRight size={15} className="text-gray-400 shrink-0" />}
                  <KeyRound size={15} className="text-blue-600 shrink-0" />
                  <h3 className="text-sm font-semibold text-gray-900">{owner}</h3>
                  <span className="text-xs text-gray-400">· {items.length} contrat{items.length > 1 ? 's' : ''}</span>
                </button>
                {open && renderTable(items)}
              </div>
            )
          })}
        </div>
      ) : (
        renderTable(filtered)
      )}
    </div>
  )
}
