/**
 * Droits côté UI. La sécurité réelle est imposée par le backend ; ces helpers
 * servent à masquer les actions non autorisées (meilleure UX).
 *
 * Le COMPTABLE est un sous-compte de gestion en LECTURE SEULE : il consulte tout
 * (biens, locataires, comptes) et encaisse les paiements, mais n'administre rien
 * (pas de création/modification/suppression de biens, locataires, annonces...).
 */
const MANAGE_ROLES = ['admin', 'gestionnaire', 'gestionnaire_proprio']

/** Peut administrer (créer/modifier/supprimer) les biens, locataires, propriétaires, annonces. */
export function canManage(role?: string | null): boolean {
  return !!role && MANAGE_ROLES.includes(role)
}

/** Sous-compte comptable (lecture seule + encaissement). */
export function isComptable(role?: string | null): boolean {
  return role === 'comptable'
}
