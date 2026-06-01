# Architecture technique — Le Comptoir Immo & Alice

Deux applications distinctes mais couplées, déployées ensemble sur un VPS OVH via
Docker Compose, derrière un reverse proxy nginx, et partageant **une seule base
PostgreSQL**.

- **Le Comptoir Immo (LeCI)** — l'application de gestion locative (gestionnaires,
  propriétaires, locataires). Domaine : `immo.lecomptoir.services`.
- **Alice** — le back-office SaaS (administration des comptes gestionnaires, plans
  tarifaires, licences, facturation, demandes). Domaine : `alice.lecomptoir.services`.

---

## 1. Vue d'ensemble (composants)

```mermaid
flowchart TB
    subgraph Clients
        U1["Navigateur<br/>Gestionnaire / Propriétaire / Locataire"]
        U2["Navigateur<br/>Admin Alice"]
        BAN["API Base Adresse Nationale<br/>(api-adresse.data.gouv.fr)"]
    end

    subgraph VPS["VPS OVH — AlmaLinux · Docker Compose"]
        NGINX["nginx<br/>reverse proxy + TLS"]

        subgraph LECI["Le Comptoir Immo"]
            FE["frontend<br/>React + Vite (nginx static)"]
            BE["backend<br/>FastAPI :8000"]
        end

        subgraph ALC["Alice"]
            AFE["alice-frontend<br/>React + Vite (nginx static)"]
            ABE["alice-backend<br/>FastAPI :8001"]
        end

        PG[("PostgreSQL<br/>base 'lecomptoirimmo'<br/>tables LeCI + tables alice_*")]
    end

    SMTP["SMTP (OVH/Brevo…)<br/>e-mails — optionnel"]

    U1 -->|"immo.lecomptoir.services"| NGINX
    U2 -->|"alice.lecomptoir.services"| NGINX
    NGINX --> FE
    NGINX --> AFE
    FE -->|"/api/v1 (JWT)"| BE
    AFE -->|"/api/v1 (JWT admin)"| ABE
    U1 -. "autocomplétion CP/ville" .-> BAN

    BE --> PG
    ABE --> PG

    BE -->|"HTTP interne X-Internal-Key<br/>licence, factures"| ABE
    ABE -->|"webhook X-Internal-Key<br/>block / unblock / plan_changed"| BE
    BE -. "lecture directe alice_* (entitlements, licence)" .-> PG
    BE -. "leads souscription/résiliation<br/>(alice_subscription_requests)" .-> PG

    BE -.-> SMTP
    ABE -.-> SMTP
```

---

## 2. Stack technique

| Couche | Le Comptoir Immo | Alice |
|---|---|---|
| Frontend | React 18 + TypeScript, Vite, Tailwind, react-router-dom, react-hook-form + Zod, Zustand, Axios, lucide-react | idem (sous-ensemble) |
| Backend | FastAPI (async), SQLAlchemy 2 async, Pydantic v2, JWT (auth) | FastAPI (async), SQLAlchemy 2 async, Pydantic v2 |
| PDF | Jinja2 + xhtml2pdf (bail, attestation de loyer, tiers payant, avis, quittances) | xhtml2pdf (factures) |
| Base de données | PostgreSQL (asyncpg) — base partagée `lecomptoirimmo` | mêmes tables (préfixe `alice_*`) dans la même base |
| Conteneurs | `backend`, `frontend` | `alice-backend`, `alice-frontend` |
| Infra commune | `postgres`, `nginx`, Docker Compose, VPS OVH AlmaLinux | — |

---

## 3. Modèle de données (principales entités)

```mermaid
erDiagram
    USERS ||--o{ PROPERTIES : "created_by"
    OWNERS ||--o{ PROPERTIES : "owner_id"
    PROPERTIES ||--o{ LEASES : "property_id"
    TENANTS ||--o{ LEASES : "tenant_id (principal)"
    TENANTS }o--o{ LEASES : "co-titulaires (lease_tenants)"
    LEASES ||--o{ AVIS_ECHEANCES : ""
    LEASES ||--o{ PAYMENTS : ""
    USERS ||--o| OWNERS : "user_id (compte ↔ fiche)"
    USERS ||--o| TENANTS : "user_id (compte ↔ fiche)"

    ALICE_PLANS ||--o{ ALICE_LICENSES : "plan_id"
    USERS ||--o| ALICE_LICENSES : "gestionnaire_user_id"
    ALICE_PLANS {
        jsonb features "fonctionnalités incluses"
    }
    ALICE_LICENSES {
        bool is_blocked
        timestamp access_until "résiliation différée"
    }
    ALICE_SUBSCRIPTION_REQUESTS {
        string source "site / résiliation"
        string status
    }
    ALICE_FEATURE_REGISTRY {
        jsonb known_keys "auto-ajout des nouvelles features"
    }
```

- `users` (LeCI) porte `full_name` (= **nom de la résidence**), `owner_full_name`
  (= **bailleur** sur les documents), `role`, coordonnées.
- Le **RIB du bailleur** vit sur la fiche `owners` (source unique).
- Les tables `alice_*` (plans, licences, factures, demandes, registre features)
  vivent dans la **même base** → Alice les écrit, LeCI les lit directement quand
  c'est pertinent (entitlements, contrôle de licence en repli).

---

## 4. Intégration LeCI ↔ Alice

```mermaid
sequenceDiagram
    participant G as Gestionnaire (navigateur)
    participant BE as LeCI backend
    participant ABE as Alice backend
    participant PG as PostgreSQL

    Note over G,BE: Connexion / usage quotidien (JWT)
    G->>BE: GET /subscription
    BE->>ABE: GET /internal/license/{user} (X-Internal-Key)
    ABE->>PG: lit alice_licenses ⋈ alice_plans
    ABE-->>BE: { plan, is_blocked, property_limit, access_until, features }
    BE-->>G: abonnement + fonctionnalités autorisées

    Note over BE,PG: Enforcement des fonctionnalités (entitlements)
    G->>BE: GET /payments (ex.)
    BE->>PG: lit alice_plans.features (require_feature)
    BE-->>G: 200 ou 403 si non incluse

    Note over ABE,BE: Action admin dans Alice
    ABE->>BE: webhook /internal/webhook/alice (block / unblock / plan_changed)
```

**Mécanismes transverses clés :**

- **Authentification** : JWT (access/refresh) ; rôles `admin`, `gestionnaire`,
  `gestionnaire_proprio`, `proprietaire`, `locataire`, `lecture`. Hiérarchie de
  permissions côté backend (`require_role`).
- **Entitlements par plan** : `alice_plans.features` (liste de clés). Appliqué
  côté LeCI au **menu** (sidebar), à l'**URL** (garde de route) et à l'**API**
  (`require_feature`/`require_any_feature`). `features = null` ⇒ toutes autorisées.
- **Auto-ajout des nouvelles fonctionnalités** : catalogue backend Alice
  (`core/feature_catalog.py`) + `alice_feature_registry` ; au démarrage, toute
  nouvelle clé est propagée (cochée) aux plans existants.
- **Licence / résiliation différée** : `access_until` (fin de mois) ; blocage
  appliqué paresseusement au prochain contrôle de licence (pas de cron).
- **Souscription / résiliation** : formulaires publics LeCI → table partagée
  `alice_subscription_requests` → traités dans Alice (« Demandes »).
- **Documents PDF** : Jinja2 → xhtml2pdf (bail non meublé loi 89-462, attestation
  de loyer CERFA 10842*07, formulaire tiers payant CERFA 11362*04, avis, quittances).
- **Autocomplétion adresse** : le frontend LeCI appelle directement la Base
  Adresse Nationale (API publique, sans backend).
- **E-mails** : `email_service` (SMTP) — câblé mais désactivé tant que SMTP non
  configuré (les envois sont alors des no-op).

---

## 5. Déploiement

```mermaid
flowchart LR
    DEV["Poste dev<br/>git + build local"] -->|"git push"| GH["GitHub<br/>origin/main"]
    DEV -->|"tar ustar + scp"| VPS["VPS OVH"]
    VPS -->|"docker compose up -d --build<br/>(service ciblé)"| RUN["Conteneurs<br/>backend / frontend /<br/>alice-backend / alice-frontend"]
    RUN --> PG[("postgres<br/>(migrations légères au démarrage :<br/>create_all + ALTER IF NOT EXISTS)")]
```

- **Reverse proxy** : nginx route les deux domaines vers les frontends statiques
  et proxifie `/api` vers les backends.
- **Migrations** : au démarrage des backends — `create_all` pour les nouvelles
  tables + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (idempotent) pour les
  nouvelles colonnes. (Alembic présent pour l'historique.)
- **Env** : `backend/.env.prod` et `alice/backend/.env.prod` (clés `ALICE_URL`,
  `ALICE_INTERNAL_KEY`/`INTERNAL_API_KEY`, `LECI_URL`, `DATABASE_URL`, `SMTP_*`).
```
