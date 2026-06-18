import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { CheckCircle2, FileUp, Loader2, ShieldCheck, UploadCloud } from 'lucide-react'
import { publicCandidatureApi, type PublicCandidature } from '@/api/publicCandidature'
import { toast } from '@/store/toast'
import { getErrorMessage } from '@/utils/errors'

const NAVY = '#0D2F5C'

export default function CandidatureUpload() {
  const { token } = useParams<{ token: string }>()
  const [data, setData] = useState<PublicCandidature | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [uploadingKey, setUploadingKey] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const inputs = useRef<Record<string, HTMLInputElement | null>>({})

  const load = () => {
    if (!token) return
    publicCandidatureApi.get(token)
      .then(r => setData(r.data))
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }
  useEffect(load, [token])

  const onPick = async (key: string, file?: File) => {
    if (!file || !token) return
    setUploadingKey(key)
    setErrors(e => { const n = { ...e }; delete n[key]; return n })
    try {
      await publicCandidatureApi.upload(token, key, file)
      const r = await publicCandidatureApi.get(token)
      setData(r.data)
      toast.success('Document reçu.')
    } catch (err) {
      const reason = getErrorMessage(
        err,
        'Format ou taille non acceptés (PDF, image, Word, Excel ; 20 Mo max).',
      )
      setErrors(e => ({ ...e, [key]: reason }))
      toast.error(reason)
    } finally {
      setUploadingKey(null)
    }
  }

  const submit = async () => {
    if (!token) return
    setSubmitting(true)
    try {
      await publicCandidatureApi.submit(token)
      setSubmitted(true)
    } catch {
      toast.error('Action impossible pour le moment.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Chargement…</div>
  }
  if (notFound || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-center px-6">
        <ShieldCheck size={40} className="text-gray-300 mb-3" />
        <h1 className="text-xl font-bold text-gray-900">Lien indisponible</h1>
        <p className="text-gray-500 mt-1 text-sm">Ce lien de dépôt n'est plus valable. Contactez votre gestionnaire.</p>
      </div>
    )
  }

  const total = data.documents.length
  const providedCount = data.documents.filter(d => d.provided).length
  const allProvided = total > 0 && providedCount === total

  const docStatus = (d: { provided: boolean; verified?: boolean }) =>
    d.verified
      ? { label: 'Validé', cls: 'bg-emerald-100 text-emerald-700' }
      : d.provided
        ? { label: 'Reçu', cls: 'bg-blue-100 text-blue-700' }
        : { label: 'À fournir', cls: 'bg-amber-100 text-amber-700' }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold" style={{ background: NAVY }}>LC</div>
          <span className="font-semibold text-gray-900 text-sm">Le Comptoir Immo</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6">
        {submitted ? (
          <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
            <CheckCircle2 size={44} className="mx-auto mb-3 text-emerald-500" />
            <h1 className="text-xl font-bold text-gray-900">Merci, c'est transmis !</h1>
            <p className="text-gray-500 text-sm mt-2">
              Votre gestionnaire a été informé. Il étudiera votre dossier et reviendra vers vous.
            </p>
          </div>
        ) : (
          <>
            <div className="mb-5">
              <h1 className="text-2xl font-bold text-gray-900">Vos pièces justificatives</h1>
              <p className="text-gray-500 text-sm mt-1">
                Bonjour {data.candidate_name}, dans le cadre de votre candidature pour{' '}
                <span className="font-medium text-gray-700">{data.property_name}</span>, merci de déposer les documents demandés.
              </p>
            </div>

            {/* Progression */}
            {total > 0 && (
              <div className={`mb-3 flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${allProvided ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
                {allProvided ? <CheckCircle2 size={16} /> : <FileUp size={16} />}
                <span>
                  {providedCount} / {total} pièce{total > 1 ? 's' : ''} déposée{providedCount > 1 ? 's' : ''}
                  {allProvided ? ' : tout est complet, vous pouvez confirmer.' : ' : déposez les pièces restantes.'}
                </span>
              </div>
            )}

            <div className="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100">
              {data.documents.map(d => {
                const st = docStatus(d)
                return (
                <div key={d.key} className="flex items-center justify-between gap-3 px-4 py-3.5">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900">{d.label}</p>
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full shrink-0 ${st.cls}`}>{st.label}</span>
                    </div>
                    {d.provided && (
                      <p className="text-xs text-gray-500 flex items-center gap-1 mt-0.5 truncate">
                        <CheckCircle2 size={12} className="text-emerald-500" /> {d.filename || 'Document reçu'}
                      </p>
                    )}
                    {errors[d.key] && (
                      <p className="text-xs text-red-600 mt-0.5">{errors[d.key]}</p>
                    )}
                  </div>
                  <input
                    ref={el => { inputs.current[d.key] = el }}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx"
                    className="hidden"
                    onChange={e => onPick(d.key, e.target.files?.[0])}
                  />
                  <button
                    onClick={() => inputs.current[d.key]?.click()}
                    disabled={uploadingKey === d.key}
                    className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 ${
                      d.provided ? 'border border-gray-200 text-gray-600 hover:bg-gray-50' : 'text-white'
                    }`}
                    style={d.provided ? undefined : { background: NAVY }}
                  >
                    {uploadingKey === d.key
                      ? <><Loader2 size={13} className="animate-spin" /> Envoi…</>
                      : d.provided
                        ? <><FileUp size={13} /> Remplacer</>
                        : <><UploadCloud size={13} /> Déposer</>}
                  </button>
                </div>
                )
              })}
              {data.documents.length === 0 && (
                <p className="px-4 py-6 text-sm text-gray-400 text-center">Aucune pièce n'est demandée pour le moment.</p>
              )}
            </div>

            <p className="text-xs text-gray-400 mt-3">Formats acceptés : PDF, image (JPG, PNG, WEBP), Word, Excel. 20 Mo maximum par fichier.</p>

            <button
              onClick={submit}
              disabled={!allProvided || submitting}
              className="mt-5 w-full py-3 rounded-xl text-white font-semibold disabled:opacity-50"
              style={{ background: NAVY }}
            >
              {submitting ? 'Envoi…' : allProvided ? "J'ai transmis tous mes documents" : 'Déposez toutes les pièces pour confirmer'}
            </button>
          </>
        )}
      </main>
    </div>
  )
}
