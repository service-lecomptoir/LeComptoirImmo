/** Utilitaires de formatage d'affichage (saisie plus lisible). */

/** Ne garde que les chiffres d'une chaîne. */
export const digitsOnly = (v: string): string => (v || '').replace(/\D/g, '')

/**
 * Regroupe les chiffres d'un numéro de téléphone par paires : « 0694123456 »
 * → « 06 94 12 34 56 ». N'altère pas la valeur stockée (purement visuel).
 */
export const formatPhoneGroups = (local: string): string =>
  digitsOnly(local).replace(/(\d{2})(?=\d)/g, '$1 ')

/**
 * Numéro de sécurité sociale (NIR) : 15 chiffres groupés
 * « 1 99 11 33 123 456 78 » (sexe · année · mois · département · commune ·
 * ordre · clé). Le groupage s'applique progressivement à la saisie.
 */
const NIR_GROUPS = [1, 2, 2, 2, 3, 3, 2]
export const formatNir = (value: string): string => {
  const d = digitsOnly(value).slice(0, 15)
  const out: string[] = []
  let i = 0
  for (const g of NIR_GROUPS) {
    if (i >= d.length) break
    out.push(d.slice(i, i + g))
    i += g
  }
  return out.join(' ')
}
