import { useEffect, useMemo, useState } from 'react'
import { Landmark, Search, FileDown, Loader2, CalendarClock, ExternalLink, ChevronRight, ChevronDown, KeyRound } from 'lucide-react'
import { leasesApi } from '@/api/leases'
import { lettersApi } from '@/api/payments'
import type { LeaseListItem } from '@/types/lease'
import { docFilename } from '@/utils/filename'
import { toast } from '@/store/toast'
import { useAuthStore } from '@/store/authStore'

const CAF_PARTENAIRES_URL = 'https://partenaires.caf.fr/cnafappli/authentificationpartenaireappli/dist/#/connexion'

export default function DocumentsCaf() {
  const [leases, setLeases] = useState<LeaseListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [downloading, setDownloading] = useState<string | null>(null)
  // Rappel de déclaration de loyer à la CAF : période juillet → décembre.
  const declarationPeriod = new Date().getMonth() >= 6 // 6 = juillet … 11 = décembre
  // Mandataire : contrats regroupés par propriétaire (pliable), comme les autres onglets.
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

  const download = async (
    lease: LeaseListItem,
    kind: 'attestation' | 'versement',
  ) => {
    const key = `${lease.id}:${kind}`
    setDownloading(key)
    try {
      if (kind === 'attestation') {
        await lettersApi.downloadAttestationCaf(
          lease.id,
          docFilename('attestation_loyer_caf', {
            tenant: lease.tenant_full_name,
            property: lease.property_name,
            year: new Date().getFullYear(),
          }),
        )
      } else {
        await lettersApi.downloadVersementDirect(
          lease.id,
          docFilename('formulaire_tiers_payant', {
            tenant: lease.tenant_full_name,
            property: lease.property_name,
            year: new Date().getFullYear(),
          }),
        )
      }
    } catch {
      toast.error('Génération du document impossible')
    } finally {
      setDownloading(null)
    }
  }

  // Regroupement par propriétaire (mandataire), ordre alphabétique.
  const ownerGroups: [string, LeaseListItem[]][] = (() => {
    const acc: Record<string, LeaseListItem[]> = {}
    for (const l of filtered) {
      const key = l.owner_name || 'Sans propriétaire'
      ;(acc[key] ||= []).push(l)
    }
    return Object.entries(acc).sort((a, b) => a[0].localeCompare(b[0], 'fr'))
  })()

  const renderRow = (l: LeaseListItem) => (
    <tr key={l.id} className="hover:bg-blue-50/40 transition-colors">
      <td className="px-6 py-4 text-sm font-medium text-gray-900">{l.tenant_full_name}</td>
      <td className="px-6 py-4 text-sm text-gray-600">{l.property_name}</td>
      <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
        {l.start_date ? new Date(l.start_date).toLocaleDateString('fr-FR') : '—'}
      </td>
      <td className="px-6 py-4">
        <div className="flex flex-col sm:flex-row sm:justify-end gap-2">
          <button
            onClick={() => download(l, 'attestation')}
            disabled={downloading === `${l.id}:attestation`}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors disabled:opacity-60 whitespace-nowrap"
          >
            {downloading === `${l.id}:attestation` ? <Loader2 size={15} className="animate-spin" /> : <FileDown size={15} />}
            Attestation de loyer
          </button>
          <button
            onClick={() => download(l, 'versement')}
            disabled={downloading === `${l.id}:versement`}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-white border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors disabled:opacity-60 whitespace-nowrap"
          >
            {downloading === `${l.id}:versement` ? <Loader2 size={15} className="animate-spin" /> : <FileDown size={15} />}
            Formulaire tiers payant
          </button>
        </div>
      </td>
    </tr>
  )

  const renderTable = (items: LeaseListItem[]) => (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-x-auto">
      <table className="w-full min-w-[640px]">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50">
            <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Locataire</th>
            <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Bien</th>
            <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Depuis le</th>
            <th className="px-6 py-3.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Documents</th>
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
          <p className="text-gray-500 text-sm">Génération de l'attestation de loyer (CERFA 10842*07) pour la CAF / MSA</p>
        </div>
      </div>

      {declarationPeriod ? (
        <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <CalendarClock size={18} className="mt-0.5 shrink-0 text-amber-600" />
          <div>
            <span className="font-semibold">La déclaration de loyers à la CAF est ouverte (juillet → décembre).</span>{' '}
            En tant que gestionnaire, déclarez les loyers de chaque locataire bénéficiaire directement sur la
            plateforme partenaires de la CAF.
            <a
              href={CAF_PARTENAIRES_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1.5 font-semibold text-amber-900 underline hover:text-amber-700"
            >
              Accéder à la plateforme partenaires CAF <ExternalLink size={14} />
            </a>
          </div>
        </div>
      ) : (
        <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
          <CalendarClock size={18} className="mt-0.5 shrink-0 text-gray-400" />
          <div>
            La déclaration de loyers n'est pas ouverte actuellement. Vous serez informé de son ouverture
            (elle a lieu de juillet à décembre).
          </div>
        </div>
      )}

      <p className="text-sm text-gray-500 mb-6 max-w-2xl">
        Sélectionnez un contrat : l'attestation de loyer et le formulaire tiers payant sont pré-remplis à
        partir des informations du bailleur, du locataire et du bail. Le bailleur n'a plus qu'à les vérifier
        et les signer.
      </p>

      <div className="relative mb-5 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Rechercher par locataire ou bien…"
          className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="animate-spin text-blue-600" size={28} />
        </div>
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
