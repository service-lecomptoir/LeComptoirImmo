/**
 * Exporte des données tabulaires en CSV et déclenche le téléchargement.
 *
 * Encodage : UTF-16 LE avec BOM (FF FE). C'est le format le plus fiable pour
 * Excel (toutes versions / locales) — contrairement à l'UTF-8 + BOM qu'Excel FR
 * ignore parfois à l'ouverture par double-clic, ce qui cassait les accents.
 * Séparateur `;` (séparateur de liste par défaut d'Excel FR).
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

  // Encodage UTF-16 LE + BOM : chaque unité de code sur 2 octets (little-endian).
  const buf = new Uint8Array(2 + content.length * 2)
  buf[0] = 0xFF
  buf[1] = 0xFE
  for (let i = 0; i < content.length; i++) {
    const code = content.charCodeAt(i)
    buf[2 + i * 2] = code & 0xFF
    buf[3 + i * 2] = (code >> 8) & 0xFF
  }
  const blob = new Blob([buf], { type: 'text/csv;charset=utf-16le;' })

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
