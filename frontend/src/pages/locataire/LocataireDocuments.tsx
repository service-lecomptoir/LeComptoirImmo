import { useState, useEffect } from 'react'
import { FileText, Download } from 'lucide-react'
import { format } from 'date-fns'
import { fr } from 'date-fns/locale'

// Pour l'instant on liste les documents via l'API documents généraux
// (la route backend filtre déjà par locataire connecté si rôle LOCATAIRE)
const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function LocataireDocuments() {
  const [documents, setDocuments] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    fetch(`${apiBase}/api/v1/documents?limit=50`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : []
        setDocuments(list)
      })
      .catch(() => { })
      .finally(() => setIsLoading(false))
  }, [])

  const handleDownload = (doc: any) => {
    const token = localStorage.getItem('access_token')
    fetch(`${apiBase}/api/v1/documents/${doc.id}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.blob())
      .then(blob => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = doc.filename ?? doc.original_filename ?? 'document'
        a.click()
      })
      .catch(() => { })
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mes documents</h1>
        <p className="text-gray-500 text-sm mt-1">Contrats, quittances et pièces jointes</p>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400 text-sm">
          Chargement…
        </div>
      ) : documents.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-16 text-center text-gray-400">
          <FileText size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Aucun document disponible</p>
          <p className="text-sm mt-1">Vos documents seront disponibles ici une fois ajoutés par votre gestionnaire.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Document</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {documents.map((d: any) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-blue-500" />
                      <p className="text-sm text-gray-900">{d.original_filename ?? d.filename ?? 'Document'}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full capitalize">
                      {d.document_type ?? d.type ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-500">
                      {d.created_at
                        ? format(new Date(d.created_at), 'd MMM yyyy', { locale: fr })
                        : '—'}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDownload(d)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-blue-600 hover:bg-blue-50 border border-blue-200 transition-colors"
                    >
                      <Download size={12} />
                      Télécharger
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
