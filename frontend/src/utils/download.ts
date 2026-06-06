// Téléchargement de fichiers (PDF…) robuste, notamment pour Safari iOS.
//
// Deux pièges corrigés :
//  1) Révocation trop tôt de l'URL blob : sur iOS Safari, `URL.revokeObjectURL`
//     appelé juste après `link.click()` annule le téléchargement → on diffère.
//  2) Ouvrir/afficher le fichier suspend la SPA et AVORTE les requêtes en cours
//     (ex. un rafraîchissement de liste) → axios remonte une « erreur réseau »
//     qui n'en est pas une. On ouvre une courte fenêtre pendant laquelle
//     l'intercepteur ignore ces avortements collatéraux.

let _suppressUntil = 0

/** Vrai si un téléchargement vient d'être déclenché (fenêtre anti-faux-positif). */
export function isDownloadSuppressing(): boolean {
  return Date.now() < _suppressUntil
}

/** Déclenche le téléchargement d'un blob et gère proprement le cycle de vie de l'URL. */
export function downloadBlob(data: BlobPart, filename: string, type = 'application/pdf'): void {
  _suppressUntil = Date.now() + 8000
  const blob = data instanceof Blob ? data : new Blob([data], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  // Révocation différée : laisse le navigateur (surtout iOS) lire le blob.
  setTimeout(() => {
    link.remove()
    URL.revokeObjectURL(url)
  }, 6000)
}
