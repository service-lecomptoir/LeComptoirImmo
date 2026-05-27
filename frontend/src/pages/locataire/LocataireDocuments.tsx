import { useState, useEffect, useRef } from 'react'
import {
  FileText, Download, Upload, ChevronDown, ChevronRight,
  FileCheck, Home, Shield, RefreshCw, TrendingUp, Trash2, X,
} from 'lucide-react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

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

// ── Mapping document types → catégories ──────────────────────────────────────

type CategoryKey =
  | 'bail'
  | 'quittances'
  | 'etats_des_lieux'
  | 'assurance'
  | 'regularisation_charges'
  | 'revision_loyer'
  | 'taxe_ordures'
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
  attestation_caf: 'Attestation CAF',
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
  const [isLoading, setIsLoading] = useState(true)
  const [collapsed, setCollapsed] = useState<Set<CategoryKey>>(new Set())
  const [uploadingFor, setUploadingFor] = useState<CategoryKey | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  // ── Chargement des documents ──────────────────────────────────────────────
  const loadDocs = async () => {
    setIsLoading(true)
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
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { loadDocs() }, [])

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
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = doc.file_name ?? 'document'
      a.click()
    } catch {
      // silently ignore
    }
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
        setUploadError(err?.detail ?? 'Erreur lors de l\'upload')
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
  const renderDocRow = (doc: Doc) => (
    <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
      <td className="px-4 py-2.5">
        <div className="flex items-center gap-2">
          <FileText size={13} className="text-blue-400 shrink-0" />
          <span className="text-sm text-gray-800 truncate max-w-xs">{doc.label || doc.file_name}</span>
        </div>
        {doc.label && doc.file_name && doc.label !== doc.file_name && (
          <p className="text-xs text-gray-400 ml-5 mt-0.5">{doc.file_name}</p>
        )}
      </td>
      <td className="px-4 py-2.5">
        <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
          {TYPE_LABELS[doc.document_type] ?? doc.document_type}
        </span>
      </td>
      <td className="px-4 py-2.5 text-sm text-gray-500 whitespace-nowrap">
        {doc.created_at
          ? format(new Date(doc.created_at), 'd MMM yyyy', { locale: fr })
          : ''}
      </td>
      <td className="px-4 py-2.5 text-right">
        <button
          onClick={() => handleDownload(doc)}
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
    const docs = documents.filter(d => cat.types.includes(d.document_type))
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
              <button
                onClick={e => { e.stopPropagation(); handleUploadClick(cat.key) }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                <Upload size={11} />
                Ajouter
              </button>
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
            <div className="border-t border-gray-100">
              <table className="w-full">
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
    <div className="p-6 max-w-4xl mx-auto">
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
