// Construction d'un nom de fichier de document (PDF) cohérent.
// Format : <prefixe>_<NomPrenomLocataire>_<NomDuBien>_<mmaaaa>.pdf
// (parties vides ignorées, tout séparé par des underscores).

function slug(s?: string | null): string {
  return (s ?? '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '') // retire les accents
    .replace(/[^a-zA-Z0-9]+/g, '_') // tout caractère non alphanumérique -> _
    .replace(/^_+|_+$/g, '')        // pas de _ en début/fin
}

export interface DocNameParts {
  tenant?: string | null
  property?: string | null
  month?: number | null
  year?: number | null
}

export function docFilename(prefix: string, parts: DocNameParts): string {
  const segments = [prefix, slug(parts.tenant), slug(parts.property)]
  if (parts.month && parts.year) {
    segments.push(`${String(parts.month).padStart(2, '0')}${parts.year}`)
  } else if (parts.year) {
    segments.push(String(parts.year))
  }
  return segments.filter(Boolean).join('_') + '.pdf'
}
