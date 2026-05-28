/**
 * Affichage des périodes de facturation (avis, loyers, quittances).
 *
 * Un appel de loyer peut couvrir plusieurs mois (fréquence trimestrielle, etc.).
 * On affiche le libellé du mois d'ancrage, et — uniquement si la période s'étale
 * sur plus d'un mois civil — la plage de dates réelle en sous-titre.
 */
export function isMultiMonth(start?: string | null, end?: string | null): boolean {
  if (!start || !end) return false
  // Comparaison sur l'année-mois (YYYY-MM)
  return start.slice(0, 7) !== end.slice(0, 7)
}
