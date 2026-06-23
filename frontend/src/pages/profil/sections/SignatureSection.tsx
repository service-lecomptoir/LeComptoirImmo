import { useRef, useState } from 'react'
import { Save, PenLine, Stamp, Upload, Trash2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useFeaturesStore } from '@/store/featuresStore'
import { isFeatureAllowed } from '@/lib/features'
import { TypedSignature } from '@/components/common/TypedSignature'
import { apiClient } from '@/api/client'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

/** Signature numérique apposée en bas des courriers générés. Section autonome
 *  (« Mes options ») avec son propre enregistrement. Inclut le tampon / cachet
 *  professionnel (mandataire), apposé à côté de la signature sur le bail et les
 *  documents CAF. */
export default function SignatureSection() {
  const { user, fetchMe } = useAuthStore()
  const features = useFeaturesStore(s => s.features)
  const tamponAllowed = isFeatureAllowed(features, 'tampon')
  // undefined = inchangée ; null = supprimée ; string = nouvelle signature.
  const [signature, setSignature] = useState<string | null | undefined>(undefined)
  const [sigMeta, setSigMeta] = useState<{ mode: string; text: string; font: string } | null>(null)
  // Tampon : même convention (undefined = inchangé ; null = supprimé ; string = nouveau).
  const [tampon, setTampon] = useState<string | null | undefined>(undefined)
  const [saving, setSaving] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  // Aperçu effectif du tampon (modification en cours sinon valeur enregistrée).
  const tamponPreview = tampon !== undefined ? tampon : (user?.tampon ?? null)

  // Suggestion de texte : nom du bailleur (société ou personne), sinon nom de compte.
  const defaultText =
    (user?.owner_kind === 'societe' ? user?.owner_company : user?.owner_full_name) || user?.full_name || ''

  const onPickTampon = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    if (!f.type.startsWith('image/')) { toast.error('Veuillez choisir une image (PNG conseillé).'); return }
    if (f.size > 2 * 1024 * 1024) { toast.error('Image trop lourde (max 2 Mo).'); return }
    const reader = new FileReader()
    reader.onload = () => setTampon(typeof reader.result === 'string' ? reader.result : null)
    reader.onerror = () => toast.error("Impossible de lire l'image.")
    reader.readAsDataURL(f)
  }

  const save = async () => {
    if (signature === undefined && tampon === undefined) {
      toast.info('Aucune modification.'); return
    }
    setSaving(true)
    try {
      const payload: Record<string, unknown> = {}
      if (signature !== undefined) {
        payload.signature = signature
        payload.signature_mode = sigMeta?.mode || null
        payload.signature_text = sigMeta?.text || null
        payload.signature_font = sigMeta?.font || null
      }
      if (tampon !== undefined) payload.tampon = tampon
      await apiClient.patch('/users/me', payload)
      await fetchMe()
      setSignature(undefined)
      setTampon(undefined)
      toast.success('Signature enregistrée')
    } catch (e) {
      toast.error(getErrorMessage(e, "Erreur lors de l'enregistrement de la signature"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <PenLine size={16} className="text-blue-600" />
        <h2 className="text-sm font-semibold text-gray-900">Signature</h2>
      </div>
      <TypedSignature
        width={230}
        value={signature !== undefined ? signature : (user?.signature ?? null)}
        initialMode={(user?.signature_mode as 'type' | 'draw' | 'upload' | null) ?? 'type'}
        initialText={user?.signature_text ?? null}
        initialFont={user?.signature_font ?? null}
        onChange={(sig) => { setSignature(sig.dataUrl); setSigMeta({ mode: sig.mode, text: sig.text, font: sig.font }) }}
        defaultText={defaultText}
      />
      <p className="text-xs text-gray-400">
        Tapez votre nom et choisissez un style d'écriture, dessinez votre signature à la souris
        (onglet « Dessin »), ou importez-en une image (onglet « Importer »). Apposée en bas de vos
        documents générés (quittance, avis d'échéance, relance).
      </p>

      {/* Tampon / cachet professionnel (mandataire) — feature configurable Alice */}
      {tamponAllowed && (
      <div className="pt-4 border-t border-gray-100 space-y-3">
        <div className="flex items-center gap-2">
          <Stamp size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">Tampon / cachet professionnel</h3>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-28 h-28 shrink-0 rounded-lg border border-dashed border-gray-300 bg-gray-50 flex items-center justify-center overflow-hidden">
            {tamponPreview
              ? <img src={tamponPreview} alt="Tampon" className="max-w-full max-h-full object-contain" />
              : <span className="text-[11px] text-gray-400 text-center px-2">Aucun tampon</span>}
          </div>
          <div className="space-y-2">
            <div className="flex gap-2">
              <button type="button" onClick={() => fileRef.current?.click()}
                className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                <Upload size={14} /> Importer une image
              </button>
              {tamponPreview && (
                <button type="button" onClick={() => setTampon(null)}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
                  <Trash2 size={14} /> Retirer
                </button>
              )}
            </div>
            <p className="text-xs text-gray-400 max-w-xs">
              PNG à fond transparent conseillé (max 2 Mo). Apposé à côté de la signature sur le bail
              et les documents CAF.
            </p>
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onPickTampon} />
        </div>
      </div>
      )}

      <div className="flex justify-end">
        <button onClick={save} disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
          <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer la signature'}
        </button>
      </div>
    </div>
  )
}
