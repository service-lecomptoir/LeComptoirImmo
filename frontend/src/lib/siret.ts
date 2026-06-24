// Validation et vérification de SIREN (9 chiffres) / SIRET (14 chiffres) français.
// - Validation hors-ligne : format + clé de Luhn (avec l'exception La Poste).
// - Vérification d'existence réelle : API publique gratuite et sans clé
//   « Recherche d'entreprises » (recherche-entreprises.api.gouv.fr).
// Tout est best-effort : un réseau indisponible n'empêche jamais la saisie.

/** Ne garde que les chiffres, max 14 (longueur d'un SIRET). */
export function cleanSiren(v: string): string {
  return (v || '').replace(/\D/g, '').slice(0, 14)
}

/** Clé de Luhn sur une chaîne de chiffres. */
function luhn(num: string): boolean {
  let sum = 0
  let alt = false
  for (let i = num.length - 1; i >= 0; i--) {
    let n = num.charCodeAt(i) - 48
    if (alt) {
      n *= 2
      if (n > 9) n -= 9
    }
    sum += n
    alt = !alt
  }
  return sum % 10 === 0
}

export type SirenKind = 'siren' | 'siret' | null

/**
 * Valide le FORMAT (longueur + clé de Luhn) d'un SIREN (9) ou SIRET (14).
 * Exception La Poste (SIREN 356000000) : valide si la somme des chiffres est
 * un multiple de 5 (ces numéros ne respectent pas Luhn).
 */
export function checkSirenSiret(v: string): { ok: boolean; kind: SirenKind } {
  const d = cleanSiren(v)
  const digitSum = (s: string) => s.split('').reduce((a, c) => a + (c.charCodeAt(0) - 48), 0)
  // La Poste (SIREN 356000000) : certains numéros ne respectent pas Luhn mais sont
  // valides si la somme des chiffres est multiple de 5. C'est une acceptation EN PLUS
  // de Luhn (jamais en remplacement), sinon on rejetterait à tort ceux qui passent Luhn.
  if (d.length === 9) {
    const laPoste = d === '356000000' && digitSum(d) % 5 === 0
    return { ok: luhn(d) || laPoste, kind: 'siren' }
  }
  if (d.length === 14) {
    const laPoste = d.startsWith('356000000') && digitSum(d) % 5 === 0
    return { ok: luhn(d) || laPoste, kind: 'siret' }
  }
  return { ok: false, kind: null }
}

export type LookupStatus = 'found' | 'not_found' | 'error'
export interface SirenLookup {
  status: LookupStatus
  /** Raison sociale / dénomination retrouvée (si trouvée). */
  name?: string
  /** SIRET du siège retourné par l'API (indicatif). */
  siret?: string
}

/**
 * Vérifie l'existence réelle d'un SIREN/SIRET au répertoire Sirene via l'API
 * publique, et renvoie la dénomination. `error` (et non `not_found`) si l'API
 * est injoignable, pour ne jamais afficher « introuvable » à tort.
 */
export async function lookupSirenSiret(v: string, signal?: AbortSignal): Promise<SirenLookup> {
  const d = cleanSiren(v)
  if (d.length !== 9 && d.length !== 14) return { status: 'not_found' }
  try {
    const url = `https://recherche-entreprises.api.gouv.fr/search?q=${d}&page=1&per_page=1`
    const r = await fetch(url, { signal })
    if (!r.ok) return { status: 'error' }
    const j = await r.json()
    const res = Array.isArray(j?.results) ? j.results[0] : null
    if (!res) return { status: 'not_found' }
    const name: string | undefined = res.nom_complet || res.nom_raison_sociale || undefined
    return { status: 'found', name, siret: res?.siege?.siret }
  } catch {
    // Inclut l'abandon volontaire (AbortError) et toute erreur réseau.
    return { status: 'error' }
  }
}
