import { Modal } from './Modal'
import { Button } from '@/components/ui'
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

const VARIANT_BUTTON: Record<ConfirmVariant, 'danger' | 'primary'> = {
  red: 'danger',
  blue: 'primary',
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
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button
            variant={VARIANT_BUTTON[confirmVariant]}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? 'En cours...' : confirmLabel}
          </Button>
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
