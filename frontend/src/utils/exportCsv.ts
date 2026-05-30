/**
 * Exporte des données tabulaires en CSV et déclenche le téléchargement.
 * - séparateur `;` (Excel FR),
 * - encodage UTF-8 explicite (TextEncoder) + BOM en octets bruts (EF BB BF)
 *   pour que les accents s'affichent correctement dans Excel / LibreOffice,
 * - échappement des guillemets / séparateurs / retours ligne.
 */
export function exportCsv(
  filename: string,
  headers: string[],
  rows: Array<Array<string | number | null | undefined>>,
): void {
  const esc = (v: string | number | null | undefined): string => {
    const s = v == null ? '' : String(v)
    return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const sep = ';'
  const content = [headers, ...rows]
    .map(r => r.map(esc).join(sep))
    .join('\r\n')

  // BOM UTF-8 en octets + contenu encodé en UTF-8 : aucune ambiguïté d'encodage.
  const bom = new Uint8Array([0xEF, 0xBB, 0xBF])
  const body = new TextEncoder().encode(content)
  const blob = new Blob([bom, body], { type: 'text/csv;charset=utf-8;' })

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
