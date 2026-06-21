# LeComptoirImmo

[![Déploiement](https://github.com/service-lecomptoir/LeComptoirImmo/actions/workflows/deploy.yml/badge.svg)](https://github.com/service-lecomptoir/LeComptoirImmo/actions/workflows/deploy.yml)

Outil de gestion locative professionnelle

---

## Démarrage rapide

### Première fois / usage normal
```
start-dev.bat          → lance backend (8000) + frontend (5173) dans 2 fenêtres séparées
start-backend.bat      → backend seul
start-frontend.bat     → frontend seul
```

### Redémarrer le backend (ex. après ajout d'une route)
```
restart-backend.bat    → tue l'ancien process, vide le cache, relance
```

---

## Notes techniques (Claude / développeurs)

### Problème pycache sur OneDrive/Windows
Python sur OneDrive peut ne pas détecter les changements de fichiers `.py` et continuer
à charger un `.pyc` stale. Tous les scripts de démarrage contiennent :
```
set PYTHONDONTWRITEBYTECODE=1
```
Cela désactive l'écriture des `.pyc` et force Python à lire les sources à chaque démarrage.

### Procédure standard pour Claude (sessions automatisées)
Pour redémarrer proprement le backend depuis une session Claude :

**1. Tuer le process Windows (PowerShell) :**
```powershell
$conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }
```

**2. Vider le pycache (bash) :**
```bash
find backend/app -name "*.pyc" -delete
find backend/app -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

**3. Démarrer uvicorn (bash) :**
```bash
cd backend && PYTHONDONTWRITEBYTECODE=1 uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

Ou en une seule commande via le script PowerShell :
```powershell
Set-Location $PSScriptRoot; .\restart-backend.ps1
```

### Stack
- **Backend** : FastAPI + SQLAlchemy async + PostgreSQL
- **Frontend** : React + TypeScript + Vite + Zustand + Tailwind
- **Auth** : JWT (access 30min + refresh 7j), stockés localStorage
- **PDF** : xhtml2pdf (pas de flexbox, pas de @page margin-boxes)
