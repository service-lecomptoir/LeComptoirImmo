// Gestion du conflit « une réévaluation est déjà programmée » renvoyé par
// l'API (PUT /leases/{id} → 409 revision_exists). Permet d'informer le
// gestionnaire et de lui proposer de remplacer, au lieu d'écraser en silence.

export interface ExistingRevision {
  kind: string
  kind_label?: string
  prev_amount: number | null
  amount: number
  effective_date: string
}

const euro = (n: number | null) =>
  n == null ? '—' : new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(n)

/** Retourne la liste des réévaluations en conflit si l'erreur est un 409
 *  « revision_exists », sinon null. */
export function getRevisionConflict(e: unknown): ExistingRevision[] | null {
  const err = e as { response?: { status?: number; data?: { detail?: { code?: string; existing?: ExistingRevision[] } } } }
  const detail = err?.response?.data?.detail
  if (err?.response?.status === 409 && detail?.code === 'revision_exists') {
    return detail.existing ?? []
  }
  return null
}

/** Message de confirmation listant la (les) réévaluation(s) déjà programmée(s). */
export function revisionReplaceConfirmMessage(existing: ExistingRevision[]): string {
  const lines = (existing || [])
    .map(r => {
      const d = new Date(r.effective_date).toLocaleDateString('fr-FR')
      return `• ${r.kind_label || r.kind} : ${euro(r.prev_amount)} → ${euro(r.amount)} au ${d}`
    })
    .join('\n')
  return `Une réévaluation est déjà programmée :\n${lines}\n\nLa remplacer par votre nouvelle valeur ?`
}
