import { describe, it, expect } from 'vitest'
import { LEASE_TYPE_LABELS, PAYMENT_METHOD_LABELS } from './lease'

describe('Libellés bail', () => {
  it('couvre les 4 types de bail', () => {
    expect(Object.keys(LEASE_TYPE_LABELS).sort()).toEqual(
      ['commercial', 'meuble', 'mobilite', 'vide'],
    )
  })

  it('couvre les 4 modes de paiement', () => {
    expect(Object.keys(PAYMENT_METHOD_LABELS).sort()).toEqual(
      ['cheque', 'especes', 'prelevement', 'virement'],
    )
  })

  it('a des libellés non vides', () => {
    for (const label of [...Object.values(LEASE_TYPE_LABELS), ...Object.values(PAYMENT_METHOD_LABELS)]) {
      expect(label.trim().length).toBeGreaterThan(0)
    }
  })
})
