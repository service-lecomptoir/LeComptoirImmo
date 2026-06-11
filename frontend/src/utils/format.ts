/** Utilitaires de formatage d'affichage (saisie plus lisible). */

/** Ne garde que les chiffres d'une chaîne. */
export const digitsOnly = (v: string): string => (v || '').replace(/\D/g, '')

/**
 * Regroupe les chiffres d'un numéro par paires lisibles. Si le nombre de
 * chiffres est impair, le 1er chiffre est isolé puis le reste par paires :
 *   « 0694123456 » (10) → « 06 94 12 34 56 »
 *   « 694123456 »  (9)  → « 6 94 12 34 56 »   (numéro local sans le 0, avec indicatif)
 * Purement visuel — n'altère pas la valeur stockée.
 */
export const groupPhoneDigits = (value: string): string => {
  const d = digitsOnly(value)
  if (d.length <= 1) return d
  const lead = d.length % 2 === 1 ? d[0] : ''
  const rest = d.slice(lead ? 1 : 0).replace(/(\d{2})(?=\d)/g, '$1 ')
  return lead ? `${lead} ${rest}` : rest
}

// Indicatifs gérés par l'application (cf. PhoneInput) — pour séparer indicatif
// et numéro local à l'affichage, du plus long au plus court (match spécifique).
const DIAL_CODES = [
  '+594', '+590', '+596', '+597', '+262', '+352', '+351',
  '+33', '+32', '+41', '+34', '+55',
].sort((a, b) => b.length - a.length)

/**
 * Affiche un téléphone stocké de façon lisible, partout (liste, mosaïque, fiche).
 *   « +594 0694420574 » → « +594 694 42 05 74 »
 * Règle : quand il y a un indicatif, on retire le 0 initial du numéro local.
 */
export const formatPhoneDisplay = (value?: string | null): string => {
  const v = (value || '').trim()
  if (!v) return ''
  const dial = DIAL_CODES.find(d => v.startsWith(d))
  if (dial) {
    const local = digitsOnly(v.slice(dial.length)).replace(/^0+/, '')
    return local ? `${dial} ${groupPhoneDigits(local)}` : dial
  }
  // Pas d'indicatif reconnu : on groupe simplement les chiffres.
  return groupPhoneDigits(v)
}

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
