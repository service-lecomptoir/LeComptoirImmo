import { useState, useEffect } from 'react'
import { Button, Input } from '@/components/ui'
import { Modal } from '@/components/common/Modal'
import { coproApi, type CoproDetail, type CoproLot, type LotInput } from '@/api/coproprietes'
import { ownersApi } from '@/api/owners'
import type { OwnerListItem } from '@/types/owner'
import { getErrorMessage } from '@/utils/errors'
import { toast } from '@/store/toast'

const LOT_TYPES = ['appartement', 'cave', 'parking', 'local commercial', 'cellier', 'garage', 'autre']

interface Props {
  copro: CoproDetail
  lot?: CoproLot
  onClose: () => void
  onSaved: () => void
}

export function CoproLotForm({ copro, lot, onClose, onSaved }: Props) {
  const isEdit = !!lot
  const [numero, setNumero] = useState(lot?.numero ?? '')
  const [lotType, setLotType] = useState(lot?.lot_type ?? 'appartement')
  const [floor, setFloor] = useState(lot?.floor ?? '')
  const [ownerId, setOwnerId] = useState(lot?.owner_id ?? '')
  const [description, setDescription] = useState(lot?.description ?? '')
  const [tantiemes, setTantiemes] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {}
    for (const k of copro.keys) init[k.id] = lot?.tantiemes?.[k.id] != null ? String(lot.tantiemes[k.id]) : ''
    return init
  })
  const [owners, setOwners] = useState<OwnerListItem[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    ownersApi.list({ limit: 500 }).then(r => setOwners(r.data.items)).catch(() => {})
  }, [])

  const lbl = 'block text-xs font-medium text-gray-700 mb-1'

  const save = async () => {
    if (!numero.trim()) { setError('Le numéro de lot est requis.'); return }
    setSaving(true); setError(null)
    const payload: LotInput = {
      numero: numero.trim(),
      lot_type: lotType || null,
      floor: floor.trim() || null,
      owner_id: ownerId || null,
      description: description.trim() || null,
      tantiemes: copro.keys
        .map(k => ({ key_id: k.id, tantiemes: parseFloat((tantiemes[k.id] || '0').replace(',', '.')) || 0 }))
        .filter(t => t.tantiemes > 0),
    }
    try {
      if (isEdit) await coproApi.updateLot(copro.id, lot!.id, payload)
      else await coproApi.createLot(copro.id, payload)
      toast.success(isEdit ? 'Lot mis à jour' : 'Lot ajouté')
      onSaved()
    } catch (e) {
      setError(getErrorMessage(e, "Erreur lors de l'enregistrement du lot."))
    } finally { setSaving(false) }
  }

  return (
    <Modal
      isOpen
      onClose={onClose}
      title={isEdit ? `Modifier le lot ${lot!.numero}` : 'Nouveau lot'}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Annuler</Button>
          <Button onClick={save} isLoading={saving}>{isEdit ? 'Enregistrer' : 'Ajouter'}</Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className={lbl}>Numéro de lot <span className="text-red-500">*</span></label>
            <Input value={numero} onChange={e => setNumero(e.target.value)} placeholder="Lot 12" />
          </div>
          <div>
            <label className={lbl}>Type</label>
            <select value={lotType} onChange={e => setLotType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              {LOT_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className={lbl}>Étage</label>
            <Input value={floor} onChange={e => setFloor(e.target.value)} placeholder="2e" />
          </div>
          <div>
            <label className={lbl}>Copropriétaire</label>
            <select value={ownerId} onChange={e => setOwnerId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">— Non renseigné —</option>
              {owners.map(o => <option key={o.id} value={o.id}>{o.full_name}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className={lbl}>Description</label>
          <Input value={description} onChange={e => setDescription(e.target.value)} placeholder="Appartement T3 côté cour" />
        </div>

        <div>
          <p className="text-xs font-semibold text-gray-700 uppercase mb-2">Tantièmes par clé de répartition</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {copro.keys.map(k => (
              <div key={k.id}>
                <label className={lbl}>{k.name} <span className="text-gray-400">/ {k.total_tantiemes}</span></label>
                <Input type="number" step="0.01" value={tantiemes[k.id] ?? ''}
                  onChange={e => setTantiemes(prev => ({ ...prev, [k.id]: e.target.value }))} placeholder="0" />
              </div>
            ))}
          </div>
          {copro.keys.length === 0 && (
            <p className="text-xs text-gray-400">Ajoutez d'abord une clé de répartition à la copropriété.</p>
          )}
        </div>
      </div>
    </Modal>
  )
}
