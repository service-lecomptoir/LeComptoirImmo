import { useState } from 'react'
import { format } from 'date-fns'
import { inspectionsApi } from '@/api/inspections'
import { getErrorMessage } from '@/utils/errors'
import type { InspectionType } from '@/types/inspection'

interface InspectionFormData {
  inspection_type: string
  inspection_date: string
  inspector_name: string
  tenant_present: boolean
  overall_condition: string
  notes: string
}

/**
 * Formulaire de création d'un état des lieux. Réutilisable : page « État des lieux »
 * (onglet Arrivée) et ailleurs. `lockedType` fige le type (ex. « entree ») et masque
 * le sélecteur ; sinon les 4 types sont proposés.
 */
export function InspectionForm({
  leaseId,
  propertyId,
  lockedType,
  onSaved,
  onCancel,
}: {
  leaseId: string
  propertyId: string
  lockedType?: InspectionType
  onSaved: () => void
  onCancel: () => void
}) {
  const today = format(new Date(), 'yyyy-MM-dd')
  const [form, setForm] = useState<InspectionFormData>({
    inspection_type: lockedType ?? 'entree',
    inspection_date: today,
    inspector_name: '',
    tenant_present: true,
    overall_condition: 'bon',
    notes: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (field: keyof InspectionFormData, value: string | boolean) =>
    setForm(f => ({ ...f, [field]: value }))

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      await inspectionsApi.create({
        lease_id: leaseId,
        property_id: propertyId,
        inspection_type: lockedType ?? form.inspection_type,
        inspection_date: form.inspection_date,
        inspector_name: form.inspector_name || undefined,
        tenant_present: form.tenant_present,
        overall_condition: form.overall_condition || undefined,
        notes: form.notes || undefined,
      })
      onSaved()
    } catch (e: any) {
      setError(getErrorMessage(e, 'Erreur lors de la création'))
    } finally {
      setSaving(false)
    }
  }

  const inp =
    'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
  const lbl = 'block text-xs font-medium text-gray-700 mb-1'

  return (
    <div className="mt-4 p-4 border border-blue-200 rounded-xl bg-blue-50 space-y-3">
      <p className="text-sm font-semibold text-blue-700">Nouvel état des lieux</p>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {!lockedType && (
          <div>
            <label className={lbl}>Type</label>
            <select
              value={form.inspection_type}
              onChange={e => set('inspection_type', e.target.value)}
              className={inp}
            >
              <option value="entree">État des lieux d'entrée</option>
              <option value="sortie">État des lieux de sortie</option>
              <option value="contradictoire">Contradictoire</option>
              <option value="periodique">Visite périodique</option>
            </select>
          </div>
        )}
        <div>
          <label className={lbl}>Date</label>
          <input
            type="date"
            value={form.inspection_date}
            onChange={e => set('inspection_date', e.target.value)}
            className={inp}
          />
        </div>
        <div>
          <label className={lbl}>Inspecteur</label>
          <input
            value={form.inspector_name}
            onChange={e => set('inspector_name', e.target.value)}
            placeholder="Nom"
            className={inp}
          />
        </div>
        <div>
          <label className={lbl}>État général</label>
          <select
            value={form.overall_condition}
            onChange={e => set('overall_condition', e.target.value)}
            className={inp}
          >
            <option value="tres_bon">Très bon</option>
            <option value="bon">Bon</option>
            <option value="moyen">Moyen</option>
            <option value="mauvais">Mauvais</option>
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="tenant_present"
          checked={form.tenant_present}
          onChange={e => set('tenant_present', e.target.checked)}
          className="w-4 h-4 text-blue-600 rounded"
        />
        <label htmlFor="tenant_present" className="text-sm text-gray-700">
          Locataire présent
        </label>
      </div>
      <div>
        <label className={lbl}>Observations</label>
        <textarea
          value={form.notes}
          onChange={e => set('notes', e.target.value)}
          rows={2}
          className={`${inp} resize-none`}
          placeholder="Remarques générales…"
        />
      </div>
      <div className="flex gap-2 justify-end">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Annuler
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Enregistrement…' : 'Enregistrer'}
        </button>
      </div>
    </div>
  )
}
