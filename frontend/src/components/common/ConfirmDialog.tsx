import { Modal } from './Modal'
import { AlertTriangle } from 'lucide-react'

type ConfirmVariant = 'red' | 'blue'

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmLabel?: string
  confirmVariant?: ConfirmVariant
  isLoading?: boolean
}

const VARIANT_CLASSES: Record<ConfirmVariant, string> = {
  red: 'bg-red-600 hover:bg-red-700',
  blue: 'bg-blue-600 hover:bg-blue-700',
}

export function ConfirmDialog({
  isOpen, onClose, onConfirm, title, message,
  confirmLabel = 'Supprimer', confirmVariant = 'red', isLoading = false,
}: ConfirmDialogProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Annuler
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 text-sm text-white rounded-lg disabled:opacity-50 ${VARIANT_CLASSES[confirmVariant]}`}
          >
            {isLoading ? 'En cours...' : confirmLabel}
          </button>
        </>
      }
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
          <AlertTriangle size={18} className="text-red-600" />
        </div>
        <p className="text-sm text-gray-600 leading-relaxed">{message}</p>
      </div>
    </Modal>
  )
}
