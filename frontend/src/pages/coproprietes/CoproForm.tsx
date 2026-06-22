import { useState } from 'react'
import { Button, Input } from '@/components/ui'
import { Modal } from '@/components/common/Modal'
import AddressAutocomplete from '@/components/common/AddressAutocomplete'
import { coproApi, type CoproDetail, type CoproInput } from '@/api/coproprietes'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

interface Props {
  copro?: CoproDetail
  onClose: () => void
  onSaved: (c: CoproDetail) => void
}

export function CoproForm({ copro, onClose, onSaved }: Props) {
  const isEdit = !!copro
  const [name, setName] = useState(copro?.name ?? '')
  const [immatriculation, setImmatriculation] = useState(copro?.immatriculation ?? '')
  const [address, setAddress] = useState(copro?.address ?? '')
  const [zipCode, setZipCode] = useState(copro?.zip_code ?? '')
  const [city, setCity] = useState(copro?.city ?? '')
  const [year, setYear] = useState(copro?.construction_year ? String(copro.construction_year) : '')
  const [notes, setNotes] = useState(copro?.notes ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const lbl = 'block text-xs font-medium text-gray-700 mb-1'

  const save = async () => {
    if (!name.trim()) { setError('Le nom de la copropriété est requis.'); return }
    setSaving(true); setError(null)
    const payload: CoproInput = {
      name: name.trim(),
      immatriculation: immatriculation.trim() || null,
      address: address.trim() || null,
      zip_code: zipCode.trim() || null,
      city: city.trim() || null,
      construction_year: year ? Number(year) : null,
      notes: notes.trim() || null,
    }
    try {
      const { data } = isEdit
        ? await coproApi.update(copro!.id, payload)
        : await coproApi.create(payload)
      toast.success(isEdit ? 'Copropriété mise à jour' : 'Copropriété créée')
      onSaved(data)
    } catch (e) {
      setError(getErrorMessage(e, "Erreur lors de l'enregistrement de la copropriété."))
    } finally { setSaving(false) }
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? 'Modifier la copropriété' : 'Nouvelle copropriété'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save} isLoading={saving}>{isEdit ? 'Enregistrer' : 'Créer'}</Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={lbl}>Nom de la copropriété <span className="text-red-500">*</span></label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="Résidence Les Tilleuls" />
          </div>
          <div>
            <label className={lbl}>N° d'immatriculation</label>
            <Input value={immatriculation} onChange={e => setImmatriculation(e.target.value)} placeholder="AA1234567" />
          </div>
        </div>
        <div>
          <label className={lbl}>Adresse</label>
          <AddressAutocomplete
            value={address}
            onChange={setAddress}
            onSelect={({ street, postcode, city: c }) => {
              setAddress(street)
              if (postcode) setZipCode(postcode)
              if (c) setCity(c)
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="12 rue de la République"
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className={lbl}>Code postal</label>
            <Input value={zipCode} onChange={e => setZipCode(e.target.value)} />
          </div>
          <div>
            <label className={lbl}>Ville</label>
            <Input value={city} onChange={e => setCity(e.target.value)} />
          </div>
          <div>
            <label className={lbl}>Année de construction</label>
            <Input type="number" value={year} onChange={e => setYear(e.target.value)} placeholder="1975" />
          </div>
        </div>
        <div>
          <label className={lbl}>Notes</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>
      </div>
    </Modal>
  )
}
