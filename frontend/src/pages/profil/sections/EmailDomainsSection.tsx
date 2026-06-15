import { useEffect, useState } from 'react'
import { AtSign, AlertTriangle, Plus, X } from 'lucide-react'
import { usersApi, type EmailDomain } from '@/api/users'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

/** Domaines e-mail autorisés pour l'envoi des communications. Section autonome. */
export default function EmailDomainsSection() {
  const [domains, setDomains] = useState<EmailDomain[]>([])
  const [newDomain, setNewDomain] = useState('')
  const [domainErr, setDomainErr] = useState<string | null>(null)
  const [domainBusy, setDomainBusy] = useState(false)

  useEffect(() => {
    usersApi.listEmailDomains().then(r => setDomains(r.data)).catch(() => {})
  }, [])

  const addDomain = async () => {
    if (!newDomain.trim()) return
    setDomainBusy(true); setDomainErr(null)
    try {
      const { data } = await usersApi.addEmailDomain(newDomain.trim())
      setDomains(prev => prev.some(d => d.id === data.id) ? prev : [...prev, data])
      setNewDomain('')
      toast.success('Domaine ajouté')
    } catch (e) {
      setDomainErr(getErrorMessage(e, "Impossible d'ajouter ce domaine"))
    } finally {
      setDomainBusy(false)
    }
  }

  const removeDomain = async (id: string) => {
    try {
      await usersApi.removeEmailDomain(id)
      setDomains(prev => prev.filter(d => d.id !== id))
      toast.success('Domaine supprimé')
    } catch {
      toast.error('Suppression impossible')
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <AtSign size={16} className="text-blue-600" />
        <h2 className="text-sm font-semibold text-gray-900">Domaines e-mail autorisés</h2>
      </div>
      <p className="text-xs text-gray-500 -mt-2">
        Ajoutez votre nom de domaine pour envoyer les communications depuis ce domaine.
      </p>
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
        <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-800">
          Attention, il n'est pas possible d'activer l'envoi depuis un nom de domaine d'un fournisseur
          public (p. ex. : @gmail.com, @hotmail.com, @yahoo.com, etc.).
        </p>
      </div>

      {domains.length > 0 && (
        <ul className="space-y-2">
          {domains.map(d => (
            <li key={d.id} className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 px-3 py-2">
              <span className="text-sm font-medium text-gray-800">{d.domain}</span>
              <button onClick={() => removeDomain(d.id)} title="Supprimer"
                className="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors">
                <X size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {domainErr && <p className="text-xs text-red-600">{domainErr}</p>}

      <div className="flex gap-2">
        <input
          className={inp}
          value={newDomain}
          onChange={e => setNewDomain(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addDomain() } }}
          placeholder="mon-agence.fr"
        />
        <button onClick={addDomain} disabled={domainBusy || !newDomain.trim()}
          className="flex items-center gap-1.5 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
          <Plus size={15} /> Ajouter un domaine
        </button>
      </div>
    </div>
  )
}
