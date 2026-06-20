# Pipeline de déploiement reproductible (GitHub Actions + ghcr.io)

Objectif : supprimer la dérive « tar-extract ». Le CI construit les images,
les pousse sur **ghcr.io**, et le **VPS ne fait que les *pull***. Ce qui tourne
en prod correspond exactement à l'image taguée par le commit (`:<sha>`).

```
push main ──▶ GitHub Actions ──▶ build immo-backend / immo-frontend
                              └─▶ push ghcr.io/service-lecomptoir/immo-*:<sha>
                              └─▶ ssh VPS : compose pull + up -d
```

## Fichiers
- `.github/workflows/deploy.yml` : build + push + déploiement SSH.
- `docker/docker-compose.deploy.yml` : compose **par images** (`image:` au lieu de
  `build:`) utilisé sur le VPS. Le `docker-compose.prod.yml` (build) reste dispo en repli.

## Étapes manuelles à faire UNE FOIS (côté toi : credentials)

> Ces étapes touchent des secrets / un compte : je ne peux pas les faire à ta place.

### 1. Secrets GitHub (repo → Settings → Secrets and variables → Actions → New secret)
| Secret | Valeur |
|---|---|
| `VPS_HOST` | `91.134.138.246` |
| `VPS_PORT` | `58007` |
| `VPS_USER` | `almalinux` |
| `VPS_SSH_KEY` | contenu de la **clé privée** de déploiement (voir étape 2) |

### 2. Clé SSH de déploiement
Génère une paire dédiée (ne réutilise pas ta clé perso) :
```bash
ssh-keygen -t ed25519 -C "github-deploy-immo" -f deploy_immo -N ""
```
- Mets la **clé publique** (`deploy_immo.pub`) dans `~/.ssh/authorized_keys` du VPS (user `almalinux`).
- Mets la **clé privée** (`deploy_immo`) dans le secret `VPS_SSH_KEY`.

### 3. Activer le déploiement automatique
Une fois les secrets ci-dessus en place : repo → Settings → **Variables** → Actions →
New variable : `DEPLOY_ENABLED` = `true`. Tant que cette variable n'est pas à `true`,
le **build + push des images tourne** (test du pipeline) mais l'étape de déploiement
SSH est **sautée** (pas de run rouge).

### 4. Autoriser le VPS à *pull* depuis ghcr.io
Les images sont privées par défaut. Deux options :
- **Simple** : rends les packages `immo-backend` / `immo-frontend` *publics*
  (GitHub → Packages → Package settings → Change visibility). Aucun login VPS requis.
- **Privé** : crée un PAT (scope `read:packages`) et sur le VPS :
  ```bash
  echo <PAT> | docker login ghcr.io -u service-lecomptoir --password-stdin
  ```

## Comment ça tourne ensuite
- Chaque push sur `main` touchant `backend/`, `frontend/` ou `docker/` déclenche le pipeline.
- Déclenchement manuel possible : onglet **Actions → Build & Deploy → Run workflow**.
- Rollback : relancer le workflow sur un commit antérieur, ou sur le VPS
  `export IMAGE_TAG=<ancien_sha> && docker compose -p docker -f docker/docker-compose.deploy.yml up -d`.

## Repli (si le CI est indisponible)
L'ancien déploiement par build reste valable :
`docker compose -p docker -f docker/docker-compose.prod.yml up -d --build`

## Généralisation
Ce pilote couvre LeComptoirImmo. Le même schéma se duplique pour Alice, Séjour,
Portail360 (un workflow + un `docker-compose.deploy.yml` par dépôt, images
`alice-*`, `sejour-*`, etc.).
