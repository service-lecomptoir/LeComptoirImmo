import { useState, useEffect, useRef } from 'react'
import {
  FileText, Download, Upload, ChevronDown, ChevronRight,
  FileCheck, Home, Shield, RefreshCw, TrendingUp, Trash2, X, Calendar, AlertTriangle,
} from 'lucide-react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { downloadBlob } from '@/utils/download'
import { docFilename } from '@/utils/filename'
import { getErrorMessage } from '@/utils/errors'
import { leasesApi } from '@/api/leases'
import { paymentsApi } from '@/api/payments'
import { avisEcheancesApi } from '@/api/avis_echeances'
import { Button } from '@/components/ui'

const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Doc {
  id: string
  file_name: string
  document_type: string
  label?: string
  notes?: string
  created_at: string
  mime_type?: string
}

// Ligne affichée : document stocké (upload) OU document généré à la volée
// (bail, quittance, avis) avec son propre déclencheur de téléchargement.
interface DocRow {
  id: string
  label: string
  typeLabel: string
  date?: string
  onDownload: () => void
}

// ── Mapping document types → catégories ──────────────────────────────────────

type CategoryKey =
  | 'bail'
  | 'avis'
  | 'quittances'
  | 'etats_des_lieux'
  | 'assurance'
  | 'regularisation_charges'
  | 'revision_loyer'
  | 'taxe_ordures'
  | 'relances'
  | 'personnels'
  | 'autres'

interface CategoryDef {
  key: CategoryKey
  label: string
  icon: React.ReactNode
  types: string[]
  uploadable?: boolean
  uploadType?: string
  description?: string
}

const CATEGORIES: CategoryDef[] = [
  {
    key: 'bail',
    label: 'Contrat de bail',
    icon: <FileText size={16} className="text-blue-600" />,
    types: ['contrat_bail', 'avenant'],
    description: 'Contrat de location et avenants',
  },
  {
    key: 'avis',
    label: "Avis d'échéances",
    icon: <Calendar size={16} className="text-blue-600" />,
    types: [],
    description: 'Vos appels de loyer, en PDF',
  },
  {
    key: 'quittances',
    label: 'Quittances de loyer',
    icon: <FileCheck size={16} className="text-green-600" />,
    types: ['quittance'],
    description: 'Quittances de loyer mensuelles',
  },
  {
    key: 'etats_des_lieux',
    label: 'États des lieux',
    icon: <Home size={16} className="text-purple-600" />,
    types: ['etat_des_lieux'],
    description: "États des lieux d'entrée et de sortie",
  },
  {
    key: 'assurance',
    label: 'Assurance habitation',
    icon: <Shield size={16} className="text-orange-600" />,
    types: ['assurance'],
    uploadable: true,
    uploadType: 'assurance',
    description: "Attestation d'assurance habitation (obligatoire)",
  },
  {
    key: 'regularisation_charges',
    label: 'Régularisation des charges locatives',
    icon: <RefreshCw size={16} className="text-teal-600" />,
    types: ['regularisation_charges'],
    description: 'Décomptes de régularisation des charges',
  },
  {
    key: 'revision_loyer',
    label: 'Révision de loyer',
    icon: <TrendingUp size={16} className="text-indigo-600" />,
    types: ['revision_loyer'],
    description: 'Avis de révision annuelle du loyer (IRL)',
  },
  {
    key: 'taxe_ordures',
    label: "Taxe d'enlèvement des ordures ménagères",
    icon: <Trash2 size={16} className="text-amber-600" />,
    types: ['taxe_ordures'],
    description: "Avis de taxe d'enlèvement des ordures ménagères",
  },
  {
    key: 'relances',
    label: 'Relances et rappels',
    icon: <AlertTriangle size={16} className="text-red-500" />,
    types: [],
    description: 'Lettres de relance pour loyer impayé',
  },
  {
    key: 'personnels',
    label: 'Documents personnels',
    icon: <FileText size={16} className="text-gray-500" />,
    types: ['cni', 'passeport', 'justificatif_domicile', 'justificatif_revenus', 'avis_imposition', 'attestation_caf', 'attestation_tiers'],
    description: 'Pièces justificatives transmises au gestionnaire',
  },
  {
    key: 'autres',
    label: 'Autres documents',
    icon: <FileText size={16} className="text-gray-400" />,
    types: ['photo', 'autre'],
    description: 'Divers',
  },
]

const TYPE_LABELS: Record<string, string> = {
  contrat_bail: 'Contrat de bail',
  avenant: 'Avenant',
  quittance: 'Quittance',
  etat_des_lieux: 'État des lieux',
  assurance: 'Assurance',
  regularisation_charges: 'Régularisation de charges',
  revision_loyer: 'Révision de loyer',
  taxe_ordures: 'T.E.O.M.',
  cni: "Carte d'identité",
  passeport: 'Passeport',
  justificatif_domicile: 'Justificatif de domicile',
  justificatif_revenus: 'Justificatif de revenus',
  avis_imposition: "Avis d'imposition",
  attestation_caf: 'Attestation de loyer',
  attestation_tiers: 'Attestation tiers',
  photo: 'Photo',
  autre: 'Autre',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

// ── Composant principal ───────────────────────────────────────────────────────

export default function LocataireDocuments() {
  const [documents, setDocuments] = useState<Doc[]>([])
  const [leases, setLeases] = useState<any[]>([])
  const [payments, setPayments] = useState<any[]>([])
  const [avis, setAvis] = useState<any[]>([])
  const [regularizations, setRegularizations] = useState<any[]>([])
  const [revisions, setRevisions] = useState<any[]>([])
  const [taxes, setTaxes] = useState<any[]>([])
  const [relances, setRelances] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  // Toutes les catégories repliées par défaut (l'utilisateur déplie au besoin).
  const [collapsed, setCollapsed] = useState<Set<CategoryKey>>(
    () => new Set(CATEGORIES.map(c => c.key))
  )
  const [uploadingFor, setUploadingFor] = useState<CategoryKey | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  // ── Chargement des documents stockés (uploads) ────────────────────────────
  const loadDocs = async () => {
    try {
      const r = await fetch(`${apiBase}/api/v1/documents?limit=200`, {
        headers: authHeaders(),
      })
      const data = await r.json()
      const list: Doc[] = Array.isArray(data)
        ? data
        : Array.isArray(data?.items)
        ? data.items
        : []
      setDocuments(list)
    } catch {
      // silently ignore
    }
  }

  // ── Chargement global : documents stockés + bail + quittances + avis ───────
  // Les quittances, le bail et les avis ne sont pas stockés comme documents : ils
  // sont générés à la volée. On les agrège ici depuis leurs sources pour qu'ils
  // soient disponibles au bon endroit (« Mes documents »).
  const loadAll = async () => {
    setIsLoading(true)
    const [, leasesR, paymentsR, avisR, regulR, revR, taxR, relR] = await Promise.allSettled([
      loadDocs(),
      leasesApi.list({ limit: 50 }),
      paymentsApi.list({ limit: 200 }),
      avisEcheancesApi.list({ limit: 200 }),
      paymentsApi.locataireRegularizations(),
      paymentsApi.locataireRevisions(),
      paymentsApi.locataireTaxes(),
      paymentsApi.locataireRelances(),
    ])
    if (leasesR.status === 'fulfilled') {
      const d: any = leasesR.value.data
      setLeases(d?.items ?? d ?? [])
    }
    if (paymentsR.status === 'fulfilled') {
      const d: any = paymentsR.value.data
      setPayments(d?.items ?? d ?? [])
    }
    if (avisR.status === 'fulfilled') setAvis(avisR.value.data ?? [])
    if (regulR.status === 'fulfilled') setRegularizations(regulR.value.data ?? [])
    if (revR.status === 'fulfilled') setRevisions(revR.value.data ?? [])
    if (taxR.status === 'fulfilled') setTaxes(taxR.value.data ?? [])
    if (relR.status === 'fulfilled') setRelances(relR.value.data ?? [])
    setIsLoading(false)
  }

  useEffect(() => { loadAll() }, [])

  // ── Auto-dismiss success ──────────────────────────────────────────────────
  useEffect(() => {
    if (!uploadSuccess) return
    const t = setTimeout(() => setUploadSuccess(null), 4000)
    return () => clearTimeout(t)
  }, [uploadSuccess])

  // ── Toggle catégorie ──────────────────────────────────────────────────────
  const toggleCollapse = (key: CategoryKey) => {
    setCollapsed(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  // ── Téléchargement ────────────────────────────────────────────────────────
  const handleDownload = async (doc: Doc) => {
    try {
      const r = await fetch(`${apiBase}/api/v1/documents/${doc.id}/download`, {
        headers: authHeaders(),
      })
      const blob = await r.blob()
      downloadBlob(blob, doc.file_name ?? 'document')
    } catch {
      // silently ignore
    }
  }

  const downloadAvis = async (a: any) => {
    try {
      const token = localStorage.getItem('access_token')
      const r = await fetch(avisEcheancesApi.pdfUrl(a.id), { headers: { Authorization: `Bearer ${token}` } })
      const blob = await r.blob()
      downloadBlob(blob, docFilename('avis_echeance', { tenant: a.tenant_full_name, property: a.property_name, month: a.period_month, year: a.period_year }))
    } catch {
      // silently ignore
    }
  }

  const fmtDate = (d?: string) => (d ? format(new Date(d), 'd MMM yyyy', { locale: fr }) : '')

  // Lignes d'une catégorie : documents stockés + documents générés (bail/quittances/avis).
  const rowsFor = (cat: CategoryDef): DocRow[] => {
    const stored: DocRow[] = documents
      .filter(d => cat.types.includes(d.document_type))
      .map(d => ({
        id: d.id,
        label: d.label || d.file_name,
        typeLabel: TYPE_LABELS[d.document_type] ?? d.document_type,
        date: d.created_at,
        onDownload: () => handleDownload(d),
      }))
    if (cat.key === 'bail') {
      const virtual = leases.map((l: any) => ({
        id: `lease-${l.id}`,
        label: `Contrat de bail${l.property_name ? ' : ' + l.property_name : ''}`,
        typeLabel: 'Contrat de bail',
        date: l.start_date ?? l.created_at,
        onDownload: () => leasesApi.downloadPdf(
          l.id, docFilename(l.lease_type === 'meuble' ? 'bail_meuble' : 'bail_non_meuble', { tenant: l.tenant_full_name, property: l.property_name }),
        ),
      }))
      return [...virtual, ...stored]
    }
    if (cat.key === 'quittances') {
      const virtual = payments
        .filter((p: any) => p.status === 'paid')
        .map((p: any) => ({
          id: `pay-${p.id}`,
          label: `Quittance : ${p.period_label}`,
          typeLabel: 'Quittance',
          date: p.payment_date,
          onDownload: () => paymentsApi.downloadQuittance(
            p.id, docFilename('quittance', { tenant: p.tenant_full_name, property: p.property_name, month: p.period_month, year: p.period_year }),
          ),
        }))
      return [...virtual, ...stored]
    }
    if (cat.key === 'avis') {
      return avis.map((a: any) => ({
        id: `avis-${a.id}`,
        label: `Avis d'échéance : ${a.period_range_label || a.period_label}`,
        typeLabel: "Avis d'échéance",
        date: a.created_at,
        onDownload: () => downloadAvis(a),
      }))
    }
    if (cat.key === 'regularisation_charges') {
      const virtual = regularizations.map((r: any) => ({
        id: `regul-${r.id}`,
        label: `Décompte de régularisation${r.period_end ? ' : ' + format(new Date(r.period_end), 'yyyy', { locale: fr }) : ''}`,
        typeLabel: 'Régularisation de charges',
        date: r.applied_at || r.period_end,
        onDownload: () => paymentsApi.downloadRegularizationPdf(
          r.id, docFilename('regularisation_charges', { year: r.period_end ? new Date(r.period_end).getFullYear() : undefined }),
        ),
      }))
      return [...virtual, ...stored]
    }
    if (cat.key === 'revision_loyer') {
      const virtual = revisions.map((rv: any) => ({
        id: `rev-${rv.lease_id}`,
        label: `Avis de révision de loyer (IRL)${rv.property_name ? ' : ' + rv.property_name : ''}`,
        typeLabel: 'Révision de loyer',
        date: rv.last_revision_date,
        onDownload: () => paymentsApi.downloadRevisionPdf(
          rv.lease_id, docFilename('revision_loyer', { property: rv.property_name }),
        ),
      }))
      return [...virtual, ...stored]
    }
    if (cat.key === 'taxe_ordures') {
      const virtual = taxes.map((t: any) => ({
        id: `taxe-${t.id}`,
        label: `Taxe d'enlèvement des ordures ménagères ${t.year}`,
        typeLabel: 'T.E.O.M.',
        date: t.declared_at,
        onDownload: () => paymentsApi.downloadTaxePdf(
          t.id, docFilename('taxe_ordures', { year: t.year }),
        ),
      }))
      return [...virtual, ...stored]
    }
    if (cat.key === 'relances') {
      return relances.map((r: any) => ({
        id: `relance-${r.id}`,
        label: r.label || 'Lettre de relance',
        typeLabel: r.rule_type === 'relance_2' ? 'Mise en demeure'
          : r.rule_type === 'relance_1' ? 'Relance' : 'Rappel',
        date: r.sent_at,
        onDownload: () => paymentsApi.downloadRelancePdf(
          r.payment_id, docFilename('relance', {}),
        ),
      }))
    }
    return stored
  }

  // ── Upload assurance ──────────────────────────────────────────────────────
  const handleUploadClick = (key: CategoryKey) => {
    setUploadingFor(key)
    setUploadError(null)
    fileRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !uploadingFor) return
    const category = CATEGORIES.find(c => c.key === uploadingFor)
    if (!category?.uploadType) return

    setUploadError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('document_type', category.uploadType)
      form.append('label', "Attestation d'assurance habitation")

      const r = await fetch(`${apiBase}/api/v1/documents/upload-locataire`, {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      })

      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        setUploadError(getErrorMessage({ response: { data: err } }, "Erreur lors de l'upload"))
      } else {
        setUploadSuccess('Document uploadé avec succès !')
        await loadDocs()
      }
    } catch {
      setUploadError('Erreur réseau. Veuillez réessayer.')
    } finally {
      setUploadingFor(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  // ── Rendu d'une ligne document ────────────────────────────────────────────
  const renderDocRow = (row: DocRow) => (
    <tr key={row.id} className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-2.5">
        <div className="flex items-center gap-2">
          <FileText size={13} className="text-blue-400 shrink-0" />
          <span className="text-sm text-gray-800 truncate max-w-xs">{row.label}</span>
        </div>
      </td>
      <td className="px-4 py-2.5">
        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
          {row.typeLabel}
        </span>
      </td>
      <td className="px-4 py-2.5 text-sm text-gray-500 whitespace-nowrap">{fmtDate(row.date)}</td>
      <td className="px-4 py-2.5 text-right">
        <button
          onClick={row.onDownload}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-blue-600 hover:bg-blue-50 border border-blue-200 transition-colors"
        >
          <Download size={11} />
          Télécharger
        </button>
      </td>
    </tr>
  )

  // ── Rendu d'une catégorie ─────────────────────────────────────────────────
  const renderCategory = (cat: CategoryDef) => {
    const docs = rowsFor(cat)
    const isOpen = !collapsed.has(cat.key)

    return (
      <div key={cat.key} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* En-tête catégorie */}
        <button
          onClick={() => toggleCollapse(cat.key)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-center">
              {cat.icon}
            </div>
            <div className="text-left">
              <p className="text-sm font-semibold text-gray-800">{cat.label}</p>
              {cat.description && (
                <p className="text-xs text-gray-400">{cat.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              docs.length > 0
                ? 'bg-blue-50 text-blue-600'
                : 'bg-gray-100 text-gray-400'
            }`}>
              {docs.length} document{docs.length > 1 ? 's' : ''}
            </span>
            {cat.uploadable && (
              <Button
                variant="primary"
                size="sm"
                onClick={e => { e.stopPropagation(); handleUploadClick(cat.key) }}
                leftIcon={<Upload size={11} />}
                className="gap-1.5"
              >
                Ajouter
              </Button>
            )}
            {isOpen
              ? <ChevronDown size={16} className="text-gray-400" />
              : <ChevronRight size={16} className="text-gray-400" />
            }
          </div>
        </button>

        {/* Table des documents */}
        {isOpen && (
          docs.length === 0 ? (
            <div className="border-t border-gray-100 px-4 py-5 text-center">
              <p className="text-sm text-gray-400">
                {cat.uploadable
                  ? "Aucun document. Cliquez sur « Ajouter » pour uploader votre attestation."
                  : "Aucun document dans cette catégorie."}
              </p>
            </div>
          ) : (
            <div className="border-t border-gray-100 overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Document</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {docs.map(renderDocRow)}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    )
  }

  // ── Render principal ──────────────────────────────────────────────────────
  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        className="hidden"
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
        onChange={handleFileSelected}
      />

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes documents</h1>
        <p className="text-gray-500 text-sm mt-1">
          Tous vos documents liés à votre location
        </p>
      </div>

      {/* Bandeau succès */}
      {uploadSuccess && (
        <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
          <FileCheck size={15} />
          {uploadSuccess}
          <button onClick={() => setUploadSuccess(null)} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Bandeau erreur */}
      {uploadError && (
        <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          {uploadError}
          <button onClick={() => setUploadError(null)} className="ml-auto">
            <X size={14} />
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400 text-sm">
          Chargement…
        </div>
      ) : (
        <div className="space-y-3">
          {CATEGORIES.map(renderCategory)}
        </div>
      )}
    </div>
  )
}
