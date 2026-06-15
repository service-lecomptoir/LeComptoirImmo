import { useState } from 'react'
import { Save, PenLine } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { TypedSignature } from '@/components/common/TypedSignature'
import { apiClient } from '@/api/client'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

/** Signature numérique apposée en bas des courriers générés. Section autonome
 *  (« Mes options ») avec son propre enregistrement. */
export default function SignatureSection() {
  const { user, fetchMe } = useAuthStore()
  // undefined = inchangée ; null = supprimée ; string = nouvelle signature.
  const [signature, setSignature] = useState<string | null | undefined>(undefined)
  const [sigMeta, setSigMeta] = useState<{ mode: string; text: string; font: string } | null>(null)
  const [saving, setSaving] = useState(false)

  // Suggestion de texte : nom du bailleur (société ou personne), sinon nom de compte.
  const defaultText =
    (user?.owner_kind === 'societe' ? user?.owner_company : user?.owner_full_name) || user?.full_name || ''

  const save = async () => {
    if (signature === undefined) { toast.info('Aucune modification de la signature.'); return }
    setSaving(true)
    try {
      await apiClient.patch('/users/me', {
        signature,
        signature_mode: sigMeta?.mode || null,
        signature_text: sigMeta?.text || null,
        signature_font: sigMeta?.font || null,
      })
      await fetchMe()
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
        initialMode={(user?.signature_mode as 'type' | 'draw' | null) ?? 'type'}
        initialText={user?.signature_text ?? null}
        initialFont={user?.signature_font ?? null}
        onChange={(sig) => { setSignature(sig.dataUrl); setSigMeta({ mode: sig.mode, text: sig.text, font: sig.font }) }}
        defaultText={defaultText}
      />
      <p className="text-xs text-gray-400">
        Tapez votre nom et choisissez un style d'écriture, ou dessinez votre signature à la souris
        (onglet « Dessin »). Apposée en bas de vos documents générés (quittance, avis d'échéance, relance).
      </p>
      <div className="flex justify-end">
        <button onClick={save} disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60">
          <Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer la signature'}
        </button>
      </div>
    </div>
  )
}
