/**
 * Exporte des données tabulaires en CSV et déclenche le téléchargement.
 * - séparateur `;` (Excel FR), BOM UTF-8 pour les accents,
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

  const blob = new Blob(['﻿' + content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
