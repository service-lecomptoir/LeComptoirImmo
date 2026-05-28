from contextlib import asynccontextmanager
import logging

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.api.v1.router import api_router
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage et nettoyage à l'arrêt."""
    logger.info(f"Démarrage de {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Vérifie la connexion DB (ping)
    logger.info("Vérification de la connexion PostgreSQL...")
    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL OK")

    # ── Création des tables manquantes (idempotent) ───────────────────────────
    try:
        import app.models  # noqa — importe tous les modèles pour que Base.metadata les connaisse
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables vérifiées / créées ✓")
    except Exception as exc:
        logger.warning(f"create_all ignoré : {exc}")

    # ── Migrations légères (colonnes manquantes) ───────────────────────────────
    await _apply_column_migrations()

    # ── Modèles par défaut : seed des comptes existants + refonte de mise en page ─
    try:
        from app.services.document_template_service import (
            backfill_all_managers, refresh_default_bodies,
        )
        async with AsyncSessionLocal() as _db:
            seeded = await backfill_all_managers(_db)
            updated = await refresh_default_bodies(_db)
            await _db.commit()
        logger.info(f"Modèles par défaut : {seeded} compte(s) dotés, {updated} mis à jour")
    except Exception as _exc:
        logger.warning(f"Backfill modèles par défaut ignoré : {_exc!r}")

    # Crée les comptes de démonstration s'ils sont absents
    logger.info("Vérification des comptes par défaut...")
    await _seed_default_users()

    # Démarre le scheduler de tâches automatiques (lit la config depuis la DB)
    logger.info("Démarrage du scheduler...")
    avis_day, avis_hour, avis_minute = 1, 7, 30
    try:
        async with AsyncSessionLocal() as _db:
            from app.services.settings_service import get_scheduler_config
            _cfg = await get_scheduler_config(_db)
            avis_day, avis_hour, avis_minute = _cfg["day"], _cfg["hour"], _cfg["minute"]
    except Exception as _exc:
        logger.warning(f"Lecture config scheduler ignorée : {_exc}")
    start_scheduler(avis_day=avis_day, avis_hour=avis_hour, avis_minute=avis_minute)

    logger.info("Application prête ✓")
    yield

    stop_scheduler()
    logger.info("Arrêt de l'application")
    await engine.dispose()


async def _seed_default_users() -> None:
    """Crée ou resynchronise les mots de passe des comptes de démonstration."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import select
    from app.models.user import User
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate
    from app.core.security import hash_password, verify_password
    from app.core.permissions import Role

    # Admin réel (toujours créé) depuis la config FIRST_ADMIN_*
    default_users = [
        UserCreate(
            email=settings.FIRST_ADMIN_EMAIL,
            password=settings.FIRST_ADMIN_PASSWORD,
            full_name=settings.FIRST_ADMIN_NAME,
            role=Role.ADMIN,
        ),
    ]

    # Comptes de démonstration : UNIQUEMENT hors production (mots de passe publics)
    if not settings.is_production:
        default_users += [
            UserCreate(
                email="gestionnaire@cabinet.fr",
                password="Gestionnaire1!",
                full_name="Gestionnaire Demo",
                role=Role.GESTIONNAIRE,
            ),
            UserCreate(
                email="gestionnaire-proprio@cabinet.fr",
                password="GestionnaireProprio1!",
                full_name="Gestionnaire-Propriétaire Demo",
                role=Role.GESTIONNAIRE_PROPRIO,
            ),
            UserCreate(
                email="proprietaire@email.fr",
                password="Proprietaire1!",
                full_name="Propriétaire Demo",
                role=Role.PROPRIETAIRE,
            ),
            UserCreate(
                email="locataire@email.fr",
                password="Locataire1!",
                full_name="Locataire Demo",
                role=Role.LOCATAIRE,
            ),
        ]

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)

    async with AsyncSessionLocal() as db:
        created, updated = [], []
        for user_data in default_users:
            result = await db.execute(select(User).where(User.email == user_data.email))
            existing = result.scalar_one_or_none()
            if existing is None:
                await UserService.create(db, user_data)
                created.append(user_data.email)
            else:
                # Bcrypt est synchrone et CPU-intensif — exécuter dans un thread
                # pour ne pas bloquer l'event loop et éviter le timeout asyncpg
                pwd_ok = await loop.run_in_executor(
                    executor, verify_password, user_data.password, existing.hashed_password
                )
                if not pwd_ok:
                    new_hash = await loop.run_in_executor(
                        executor, hash_password, user_data.password
                    )
                    existing.hashed_password = new_hash
                    updated.append(user_data.email)
        await db.commit()
        executor.shutdown(wait=False)
        for email in created:
            logger.info(f"Compte créé : {email}")
        for email in updated:
            logger.info(f"Mot de passe resynchronisé : {email}")


async def _apply_column_migrations() -> None:
    """Ajoute les colonnes manquantes (idempotent — IF NOT EXISTS).
    Les erreurs sont loguées mais ne bloquent pas le démarrage."""
    from sqlalchemy import text
    migrations = [
        # Quittances sur les paiements
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS quittance_generated_at TIMESTAMPTZ",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS quittance_sent_at TIMESTAMPTZ",
        # Déclaration de paiement par le locataire (à valider par le gestionnaire)
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS declared_at TIMESTAMPTZ",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS declared_method VARCHAR(20)",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS declared_amount NUMERIC(10,2)",
        # Crédit (avance / trop-perçu) consommé par un paiement, déduit de l'échéance suivante
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS credit_applied NUMERIC(10,2) NOT NULL DEFAULT 0",
        # Règle d'appel de loyer sur le contrat (période contractuelle / calendrier)
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS rent_call_rule VARCHAR(20) NOT NULL DEFAULT 'calendrier'",
        # Fréquence d'appel du loyer (mensuelle / bimestrielle / trimestrielle / semestrielle / annuelle)
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS payment_frequency VARCHAR(20) NOT NULL DEFAULT 'mensuelle'",
        # Période réellement couverte par un avis d'échéance (prorata d'entrée/sortie)
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS period_start DATE",
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS period_end DATE",
        # Période réellement couverte par un loyer (multi-mois selon la fréquence)
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS period_start DATE",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS period_end DATE",
        # Coordonnées profil utilisateur (gestionnaire/agence)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS address VARCHAR(300)",
        # Fusion bien/logement : caractéristiques du logement portées par le bien
        # (loyer/charges/dépôt sont sur le contrat, pas le bien → colonnes supprimées plus bas)
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS floor INTEGER",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS area_sqm NUMERIC(8,2)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS bathrooms INTEGER",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_occupied BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_available BOOLEAN NOT NULL DEFAULT true",
        # Caractéristiques étendues du bien (typologie, équipements, extérieurs)
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS typology VARCHAR(8)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS heating_type VARCHAR(30)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS energy_class VARCHAR(2)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS furnished BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS kitchen_equipped BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_elevator BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_balcony BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_terrace BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_garden BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_parking BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_cellar BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_fiber BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS has_air_conditioning BOOLEAN NOT NULL DEFAULT false",
        "UPDATE properties SET property_type='appartement' WHERE property_type='immeuble'",
        # Inspections rattachées au bien (remplace unit_id)
        "ALTER TABLE inspections ADD COLUMN IF NOT EXISTS property_id UUID REFERENCES properties(id) ON DELETE SET NULL",
        # Occupation du bien dérivée des baux actifs
        """
        UPDATE properties p SET
          is_occupied = EXISTS (SELECT 1 FROM leases l WHERE l.property_id = p.id AND l.is_active = true),
          is_available = NOT EXISTS (SELECT 1 FROM leases l WHERE l.property_id = p.id AND l.is_active = true)
        """,
        # Isolation contacts/automatisation (013)
        "ALTER TABLE contacts ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL",
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL",
        # Demandes de souscription (page d'accueil → ProxyGen). Table partagée :
        # créée ici par sécurité (le endpoint public écrit dedans) ; ProxyGen la
        # gère aussi via create_all (idempotent).
        """
        CREATE TABLE IF NOT EXISTS proxygen_subscription_requests (
            id UUID PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(30),
            company VARCHAR(200),
            message TEXT,
            source VARCHAR(50) NOT NULL DEFAULT 'site_lecomptoir',
            status VARCHAR(20) NOT NULL DEFAULT 'nouveau',
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            processed_at TIMESTAMPTZ
        )
        """,
        # App settings seed (015)
        "INSERT INTO app_settings (key, value) VALUES ('avis_generation_day', '1') ON CONFLICT DO NOTHING",
        "INSERT INTO app_settings (key, value) VALUES ('avis_generation_hour', '7') ON CONFLICT DO NOTHING",
        "INSERT INTO app_settings (key, value) VALUES ('avis_generation_minute', '30') ON CONFLICT DO NOTHING",
        # ── 016 : Entité propriétaire (fiche Owner) + lien sur le bien ───────────
        # La table `owners` est créée par create_all. On ajoute la colonne de lien
        # puis on rapatrie les propriétaires existants (comptes + owner_name) en
        # fiches, et on relie les biens. Idempotent (NOT EXISTS / owner_id IS NULL).
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES owners(id) ON DELETE SET NULL",
        # Fiches depuis les comptes propriétaire / gestionnaire-propriétaire.
        # NB : le RIB a été migré vers la fiche lors du premier déploiement ; il vit
        # désormais uniquement sur owners (colonnes users.iban/bic/bank_holder supprimées).
        """
        INSERT INTO owners (id, last_name, email, phone, address, user_id, created_by)
        SELECT gen_random_uuid(), u.full_name, u.email, u.phone, u.address, u.id, u.created_by
        FROM users u
        WHERE (u.role IN ('proprietaire', 'gestionnaire_proprio')
               OR u.id IN (SELECT DISTINCT owner_user_id FROM properties WHERE owner_user_id IS NOT NULL))
          AND NOT EXISTS (SELECT 1 FROM owners o WHERE o.user_id = u.id)
        """,
        # Relier les biens à la fiche de leur propriétaire-utilisateur
        """
        UPDATE properties p SET owner_id = o.id
        FROM owners o
        WHERE o.user_id = p.owner_user_id
          AND p.owner_user_id IS NOT NULL
          AND p.owner_id IS NULL
        """,
        # Fiches depuis les biens à propriétaire "texte" (sans compte ni fiche)
        """
        DO $$
        DECLARE r RECORD; new_id uuid;
        BEGIN
          FOR r IN SELECT id, owner_name, owner_email, owner_phone, created_by
                   FROM properties
                   WHERE owner_id IS NULL AND owner_user_id IS NULL
                     AND owner_name IS NOT NULL AND btrim(owner_name) <> ''
          LOOP
            INSERT INTO owners (id, last_name, email, phone, created_by)
            VALUES (gen_random_uuid(), r.owner_name,
                    NULLIF(btrim(r.owner_email), ''), NULLIF(btrim(r.owner_phone), ''),
                    r.created_by)
            RETURNING id INTO new_id;
            UPDATE properties SET owner_id = new_id WHERE id = r.id;
          END LOOP;
        END $$;
        """,
        # ── 017 : RIB désormais porté UNIQUEMENT par la fiche propriétaire ───────
        # Le RIB a été rapatrié vers `owners` (backfill ci-dessus) lors du 1er déploiement.
        # On retire les colonnes devenues inutiles du compte utilisateur.
        "ALTER TABLE users DROP COLUMN IF EXISTS iban",
        "ALTER TABLE users DROP COLUMN IF EXISTS bic",
        "ALTER TABLE users DROP COLUMN IF EXISTS bank_holder",
        # ── 018 : nettoyage des reliques de la fusion bien/logement ─────────────
        # Loyer/charges/dépôt sont portés par le contrat (leases), plus par le bien.
        "ALTER TABLE properties DROP COLUMN IF EXISTS base_rent",
        "ALTER TABLE properties DROP COLUMN IF EXISTS charges_amount",
        "ALTER TABLE properties DROP COLUMN IF EXISTS deposit_months",
        "ALTER TABLE properties DROP COLUMN IF EXISTS rooms",
        "ALTER TABLE properties DROP COLUMN IF EXISTS bedrooms",
        # Entité logement (units) supprimée : on retire d'abord les colonnes de lien
        # (ce qui supprime aussi leurs contraintes FK), puis la table elle-même.
        "ALTER TABLE leases DROP COLUMN IF EXISTS unit_id",
        "ALTER TABLE payments DROP COLUMN IF EXISTS unit_id",
        "ALTER TABLE avis_echeances DROP COLUMN IF EXISTS unit_id",
        "ALTER TABLE inspections DROP COLUMN IF EXISTS unit_id",
        "ALTER TABLE entretiens DROP COLUMN IF EXISTS unit_id",
        "ALTER TABLE tickets DROP COLUMN IF EXISTS unit_id",
        "DROP TABLE IF EXISTS units",
    ]
    try:
        async with engine.begin() as conn:
            for sql in migrations:
                await conn.execute(text(sql))
        logger.info("Migrations colonnes appliquées ✓")
    except Exception as exc:
        logger.warning(f"Migration colonnes ignorée (non bloquant) : {exc}")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API de gestion locative — LeComptoirImmo",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middlewares ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)

# ── Fichiers statiques (logos uploadés) ───────────────────────────────────────
os.makedirs("uploads/logos", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de vérification de santé — utilisé par Docker et le load balancer."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
