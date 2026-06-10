import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Après un déploiement, un onglet déjà ouvert peut tenter de charger un chunk
// (module/preload) dont le hash a changé. Vite émet alors « vite:preloadError ».
// On recharge la page une seule fois (garde-fou anti-boucle) pour récupérer les
// derniers assets, au lieu d'afficher une erreur applicative.
window.addEventListener('vite:preloadError', () => {
  const KEY = 'chunk-reload-ts'
  const last = Number(sessionStorage.getItem(KEY) || '0')
  if (Date.now() - last > 10000) {
    sessionStorage.setItem(KEY, String(Date.now()))
    window.location.reload()
  }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
