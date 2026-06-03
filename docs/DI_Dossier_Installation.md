# DI — Dossier d'Installation · Le Comptoir Immo

> Procédure complète pour **réinstaller l'application de zéro** (nouveau serveur ou
> reconstruction). Public : support / exploitation technique.
> Voir aussi le **DE — Dossier d'Exploitation** (`DE_Dossier_Exploitation.md`) pour
> l'exploitation courante (sauvegardes, mises à jour, dépannage).

⚠️ **Secrets** : ce document ne contient **aucun mot de passe ni clé**. Les valeurs
sensibles vivent dans les fichiers `*.env.prod` (hors Git) et dans le coffre de
secrets de l'équipe. Les placeholders sont notés `<À_RENSEIGNER>`.

---

## 1. Architecture cible

Deux applications partageant **une seule base PostgreSQL**, orchestrées par Docker
Compose derrière un reverse-proxy Nginx avec TLS Let's Encrypt.

| Composant | Conteneur | Port interne | Domaine public |
|---|---|---|---|
| PostgreSQL 16 (base partagée `lecomptoirimmo`) | `locataire_postgres` | 5432 (non exposé) | — |
| Backend Le Comptoir Immo (FastAPI) | `locataire_backend` | 8000 | via Nginx |
| Frontend Le Comptoir Immo (React/Vite → Nginx) | `locataire_frontend` | 80 | `immo.lecomptoir.services` |
| Backend Alice (FastAPI) | `alice_backend` | 8001 | via Nginx |
| Frontend Alice (React/Vite → Nginx) | `alice_frontend` | 80 | `alice.lecomptoir.services` |
| Reverse-proxy + TLS | `locataire_nginx` | 80 / 443 | — |
| Certbot (Let's Encrypt) | `locataire_certbot` | — | — |

- **Stack Compose** : `docker/docker-compose.prod.yml`
- **Code source** : `git@github.com:service-lecomptoir/LeComptoirImmo.git` (branche `main`)
- Le **frontend** est compilé au build (`vite build`) puis servi statiquement par Nginx.
- Le **backend** applique au démarrage des **migrations légères** (colonnes/enums
  manquants) et **amorce** les modèles par défaut + le compte admin initial.

---

## 2. Pré-requis serveur

- VPS Linux (référence : **OVH AlmaLinux**, IP `91.134.138.246`).
- Accès SSH administrateur (référence : alias `ssh lecomptoir-vps`, **port 58007**,
  utilisateur `almalinux`, `sudo` sans mot de passe). La clé privée SSH (`lecomptoir_vps`)
  est conservée hors Git.
- **DNS** : faire pointer `immo.lecomptoir.services` et `alice.lecomptoir.services`
  vers l'IP du serveur (enregistrements A) **avant** l'émission des certificats.
- Ports **80** et **443** ouverts dans le pare-feu.
- Logiciels : `git`, `docker` (≥ 24) et le plugin `docker compose` (v2).

### Installation Docker (AlmaLinux / RHEL-like)

```bash
sudo dnf install -y dnf-plugins-core git
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # puis se reconnecter
```

---

## 3. Récupération du code

```bash
cd ~
git clone git@github.com:service-lecomptoir/LeComptoirImmo.git
cd LeComptoirImmo
git checkout main
```

Arborescence utile :
```
LeComptoirImmo/
├── backend/            # API Le Comptoir Immo (FastAPI)
│   ├── .env            # (à créer) — lue par le conteneur postgres (POSTGRES_*)
│   └── .env.prod       # (à créer) — lue par le backend en prod
├── frontend/           # SPA React/Vite
├── alice/
│   └── backend/.env.prod   # (à créer) — backend Alice
└── docker/
    ├── docker-compose.prod.yml
    ├── nginx.conf  / nginx-site.conf
    └── Dockerfile.backend / Dockerfile.frontend / Dockerfile.alice-backend / Dockerfile.alice-frontend
```

> Les fichiers `*.env*` sont **exclus de Git** et des images Docker
> (`.dockerignore`). Ils doivent être créés manuellement à chaque réinstallation.

---

## 4. Configuration des fichiers d'environnement

La prod lit **directement** les `.env.prod` (via `env_file:` du compose). Le conteneur
`postgres` lit `backend/.env` (uniquement les variables `POSTGRES_*`).

### 4.1 `backend/.env` (variables PostgreSQL — partagées)

```dotenv
POSTGRES_DB=lecomptoirimmo
POSTGRES_USER=<À_RENSEIGNER>
POSTGRES_PASSWORD=<À_RENSEIGNER>
# Les autres clés ci-dessous évitent une erreur si ce fichier sert aussi en dev :
SECRET_KEY=<À_RENSEIGNER>
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@localhost:5432/lecomptoirimmo
```

### 4.2 `backend/.env.prod` (backend Le Comptoir Immo)

```dotenv
APP_ENV=production
DEBUG=false
SECRET_KEY=<À_RENSEIGNER>                # chaîne aléatoire longue (ex. openssl rand -hex 32)

# Base de données — hôte = nom du service compose « postgres »
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=lecomptoirimmo
POSTGRES_USER=<même que backend/.env>
POSTGRES_PASSWORD=<même que backend/.env>
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@postgres:5432/lecomptoirimmo

# CORS (domaines publics)
CORS_ORIGINS=https://immo.lecomptoir.services

# Liaison interne vers Alice (hôte = nom du service compose « alice-backend »)
ALICE_URL=http://alice-backend:8001
ALICE_INTERNAL_KEY=<À_RENSEIGNER>        # DOIT être identique à INTERNAL_API_KEY d'Alice

# SMTP (laisser SMTP_HOST vide pour désactiver l'envoi d'e-mails)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@lecomptoir.services
SMTP_FROM_NAME=Le Comptoir Immo
SMTP_TLS=true

# Optionnels
INSEE_API_KEY=                           # IRL automatique (vide = saisie manuelle)
LEADS_NOTIFY_EMAIL=
FIRST_ADMIN_EMAIL=admin@lecomptoir.services
FIRST_ADMIN_PASSWORD=<À_RENSEIGNER>
FIRST_ADMIN_NAME=Administrateur
```

### 4.3 `alice/backend/.env.prod` (backend Alice — même base)

```dotenv
APP_ENV=production
DEBUG=false
SECRET_KEY=<À_RENSEIGNER>                # propre à Alice
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@postgres:5432/lecomptoirimmo
INTERNAL_API_KEY=<identique à ALICE_INTERNAL_KEY côté Le Comptoir Immo>
```

> **Points de vigilance** (causes d'incidents passés) :
> - `ALICE_INTERNAL_KEY` (Le Comptoir Immo) **==** `INTERNAL_API_KEY` (Alice), sinon la
>   liaison inter-applications échoue.
> - Les hôtes DB/Alice sont les **noms de services compose** (`postgres`,
>   `alice-backend`), pas `localhost`.
> - La config backend est en `extra='forbid'` : **aucune clé inconnue** dans `.env.prod`,
>   sinon le backend refuse de démarrer.

---

## 5. Build & démarrage

```bash
cd ~/LeComptoirImmo
docker compose -f docker/docker-compose.prod.yml up -d --build
```

- Première exécution : build des 4 images (backend, frontend, alice-backend,
  alice-frontend) + récupération de Postgres/Nginx/Certbot. Compter quelques minutes.
- Au démarrage du backend : migrations légères + amorçage (modèles par défaut,
  compte admin initial). Le seed prend ~40 s.

Vérifier l'état :
```bash
docker compose -f docker/docker-compose.prod.yml ps
docker compose -f docker/docker-compose.prod.yml logs --tail=50 backend
```

---

## 6. Certificats TLS (Let's Encrypt)

Les certificats sont stockés dans le volume `certbot_certs` (monté en lecture seule
par Nginx). DNS doit déjà pointer sur le serveur.

Émission initiale (adapter les domaines/e-mail) :
```bash
docker compose -f docker/docker-compose.prod.yml run --rm certbot \
  certonly --webroot -w /var/www/certbot \
  -d immo.lecomptoir.services -d alice.lecomptoir.services \
  --email <CONTACT_EMAIL> --agree-tos --no-eff-email
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -s reload
```

Renouvellement (idempotent ; à planifier, cf. DE) :
```bash
docker compose -f docker/docker-compose.prod.yml run --rm certbot renew
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -s reload
```

---

## 7. Restauration des données (réinstallation avec reprise)

Si on réinstalle en **conservant les données**, restaurer un dump PostgreSQL
(cf. DE pour la création des dumps) :

```bash
# Copier le dump sur le serveur, puis :
cat dump.sql | docker compose -f docker/docker-compose.prod.yml exec -T postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Les fichiers uploadés (pièces jointes) vivent dans le volume `uploads_data`
(`/app/uploads` du backend) — à restaurer également si sauvegardé.

---

## 8. Vérification post-installation (recette de mise en service)

```bash
# Backend up (403 attendu = service en ligne mais endpoint protégé)
curl -s -o /dev/null -w "%{http_code}\n" https://immo.lecomptoir.services/api/v1/settings/scheduler   # → 403
# Frontends
curl -s -o /dev/null -w "%{http_code}\n" https://immo.lecomptoir.services/    # → 200
curl -s -o /dev/null -w "%{http_code}\n" https://alice.lecomptoir.services/   # → 200
```

- Connexion à `https://immo.lecomptoir.services` avec le compte admin initial
  (`FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD`). **Changer le mot de passe** ensuite.
- Vérifier qu'aucune erreur n'apparaît dans `logs backend` / `logs alice-backend`.

---

## 9. Récapitulatif « réinstallation de zéro » (express)

1. Provisionner le VPS, installer Docker + git, ouvrir 80/443.
2. Pointer les DNS des 2 domaines vers le serveur.
3. `git clone` du dépôt, `git checkout main`.
4. Créer `backend/.env`, `backend/.env.prod`, `alice/backend/.env.prod` (§4).
5. `docker compose -f docker/docker-compose.prod.yml up -d --build`.
6. Émettre les certificats TLS (§6) puis recharger Nginx.
7. (Optionnel) restaurer dump PostgreSQL + volume `uploads_data` (§7).
8. Vérifier la mise en service (§8) et changer les mots de passe admin.
