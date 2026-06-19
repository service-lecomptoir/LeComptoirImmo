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

    # ── Sérialisation de TOUTE l'initialisation entre workers uvicorn ──────────
    # Un seul worker exécute create_all + migrations + seeds + fixups à la fois
    # (verrou de session Postgres tenu pendant tout l'init) : aucun deadlock DDL/seed
    # ni doublon. Les autres workers attendent puis ré-exécutent (tout est idempotent).
    _init_lock_conn = await engine.connect()
    try:
        await _init_lock_conn.execute(text("SELECT pg_advisory_lock(741258)"))
    except Exception as _exc:  # noqa: BLE001 : ne jamais bloquer le démarrage
        logger.warning(f"Verrou d'initialisation indisponible : {_exc!r}")

    # ── Création des tables manquantes (idempotent) ───────────────────────────
    try:
        import app.models  # noqa : importe tous les modèles pour que Base.metadata les connaisse
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables vérifiées / créées ✓")
    except Exception as exc:
        logger.warning(f"create_all ignoré : {exc}")

    # ── Migrations légères (colonnes manquantes) ───────────────────────────────
    await _apply_column_migrations()

    # ── Valeur d'enum « pending_closure » (clôture proposée) — en AUTOCOMMIT car
    # ALTER TYPE ... ADD VALUE ne doit pas s'exécuter dans une transaction. ──────
    try:
        from sqlalchemy import text as _text
        async with engine.connect() as conn:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(_text(
                "ALTER TYPE ticket_status_enum ADD VALUE IF NOT EXISTS 'pending_closure'"))
        logger.info("Enum ticket_status_enum : valeur pending_closure ✓")
    except Exception as _exc:
        logger.warning(f"Migration enum pending_closure ignorée : {_exc!r}")

    # ── Modèles par défaut : seed des comptes existants + refonte de mise en page ─
    try:
        from sqlalchemy import text as _text
        from app.services.document_template_service import (
            backfill_all_managers, refresh_default_bodies,
        )
        async with AsyncSessionLocal() as _db:
            # (Sérialisation assurée par le verrou d'init global au démarrage.)
            # Purge des doublons de modèles PAR DÉFAUT (garde le plus ancien par
            # gestionnaire + type), sans toucher aux modèles personnalisés.
            await _db.execute(_text(
                "DELETE FROM document_templates a USING document_templates b "
                "WHERE a.gestionnaire_id = b.gestionnaire_id "
                "AND a.template_type = b.template_type "
                "AND a.is_default = true AND b.is_default = true "
                "AND a.gestionnaire_id IS NOT NULL "
                "AND (a.created_at, a.ctid) > (b.created_at, b.ctid)"
            ))
            seeded = await backfill_all_managers(_db)
            updated = await refresh_default_bodies(_db)
            await _db.commit()
        logger.info(f"Modèles par défaut : {seeded} compte(s) dotés, {updated} mis à jour")
    except Exception as _exc:
        logger.warning(f"Backfill modèles par défaut ignoré : {_exc!r}")

    # ── Statuts des avis : aligne les brouillons existants (Envoyé / Acquitté) ──
    try:
        from app.services.avis_echeance_service import AvisEcheanceService
        async with AsyncSessionLocal() as _db:
            n = await AvisEcheanceService.sync_statuses(_db)
            n2 = await AvisEcheanceService.sync_apurement_statuses(_db)
            await _db.commit()
        logger.info(f"Statuts avis synchronisés : {n} (loyer) + {n2} (apurement)")
    except Exception as _exc:
        logger.warning(f"Sync statuts avis ignoré : {_exc!r}")

    # ── Règles d'automatisation par défaut (no-régression) ─────────────────────
    # Seede les règles avis/quittance/rappels/relances pour les gestionnaires qui
    # n'en ont aucune → les envois automatiques continuent, pilotés par les règles.
    try:
        from sqlalchemy import text as _text
        from app.services.automation_engine import backfill_default_rules, backfill_default_content, backfill_rule_types
        async with AsyncSessionLocal() as _db:
            # (Sérialisation assurée par le verrou d'init global au démarrage.)
            # Nettoyage des doublons des nouveaux types déjà créés par une course
            # multi-workers (garde le plus ancien par gestionnaire + type).
            await _db.execute(_text(
                "DELETE FROM automation_rules a USING automation_rules b "
                "WHERE a.created_by = b.created_by AND a.rule_type = b.rule_type "
                "AND a.rule_type IN ('revision_loyer','revision_charges','taxe_om','rapport_mensuel') "
                "AND (a.created_at, a.ctid) > (b.created_at, b.ctid)"
            ))
            nr = await backfill_default_rules(_db)
            # Nouveaux types (révisions loyer/charges, taxe OM, rapport mensuel) sur
            # les comptes existants, sans recréer des règles supprimées.
            nr += await backfill_rule_types(_db, [
                "revision_loyer", "revision_charges", "taxe_om", "rapport_mensuel",
            ])
            nc = await backfill_default_content(_db)
            # Modèles de courrier multilingues par défaut (« Standard » sélectionné
            # par type), même verrou pour éviter les doublons entre workers.
            from app.services.message_template_defaults import backfill_default_message_templates
            nt = await backfill_default_message_templates(_db)
            await _db.commit()
        if nr:
            logger.info(f"Règles d'automatisation par défaut créées : {nr}")
        if nc:
            logger.info(f"Contenu par défaut (sujet/corps) rempli pour {nc} règle(s)")
        if nt:
            logger.info(f"Modèles de courrier multilingues par défaut créés : {nt}")
    except Exception as _exc:
        logger.warning(f"Backfill règles d'automatisation ignoré : {_exc!r}")

    # Crée les comptes de démonstration s'ils sont absents
    logger.info("Vérification des comptes par défaut...")
    await _seed_default_users()

    # ── Reprise historique des identifiants lisibles (ref_code) ────────────────
    # Attribue un ref_code aux comptes / propriétaires / biens / locataires qui
    # n'en ont pas encore (idempotent). Voir reference_service.
    try:
        from app.services.reference_service import backfill_table, user_prefix
        from app.models.user import User as _U
        from app.models.owner import Owner as _O
        from app.models.tenant import Tenant as _T
        from app.models.property import Property as _P
        async with AsyncSessionLocal() as _db:
            nu = await backfill_table(_db, _U, lambda r: user_prefix(getattr(r, "role", None)))
            no = await backfill_table(_db, _O, lambda r: "PR")
            nb = await backfill_table(_db, _P, lambda r: "BN")
            nt = await backfill_table(_db, _T, lambda r: "LO")
            await _db.commit()
        logger.info(f"Identifiants ref_code (reprise) : {nu} comptes, {no} propriétaires, {nb} biens, {nt} locataires")
    except Exception as _exc:
        logger.warning(f"Reprise ref_code ignorée : {_exc!r}")

    # Démarre le scheduler de tâches automatiques (lit la config depuis la DB)
    logger.info("Démarrage du scheduler...")
    avis_day, avis_hour, avis_minute = 1, 7, 30
    rem_hour, rem_minute = 8, 0
    try:
        async with AsyncSessionLocal() as _db:
            from app.services.settings_service import get_scheduler_config, get_reminder_config
            _cfg = await get_scheduler_config(_db)
            avis_day, avis_hour, avis_minute = _cfg["day"], _cfg["hour"], _cfg["minute"]
            _rem = await get_reminder_config(_db)
            rem_hour, rem_minute = _rem["hour"], _rem["minute"]
    except Exception as _exc:
        logger.warning(f"Lecture config scheduler ignorée : {_exc}")
    start_scheduler(
        avis_day=avis_day, avis_hour=avis_hour, avis_minute=avis_minute,
        reminder_hour=rem_hour, reminder_minute=rem_minute,
    )

    # Libère le verrou d'initialisation (les autres workers peuvent démarrer).
    try:
        await _init_lock_conn.execute(text("SELECT pg_advisory_unlock(741258)"))
    except Exception:  # noqa: BLE001
        pass
    finally:
        await _init_lock_conn.close()

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

    # Compte initial (toujours créé) depuis la config FIRST_ADMIN_*.
    # Il n'y a PLUS de compte « admin » dans LeComptoirImmo : l'administration est
    # assurée par Alice (console SaaS). Ce compte est un Gestionnaire Mandataire.
    default_users = [
        UserCreate(
            email=settings.FIRST_ADMIN_EMAIL,
            password=settings.FIRST_ADMIN_PASSWORD,
            full_name=settings.FIRST_ADMIN_NAME,
            role=Role.GESTIONNAIRE,
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
        # Sujet déclaré par le locataire sur une démarche → agent IA notifié (push)
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS topic VARCHAR(20)",
        # Photo jointe à une démarche (locataire)
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS photo_path VARCHAR(500)",
        # Publication des annonces : suivi de performance (vues de la page publique)
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS views_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS last_viewed_at TIMESTAMPTZ",
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS charges NUMERIC(10,2)",
        # Règle d'appel de loyer sur le contrat (période contractuelle / calendrier)
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS rent_call_rule VARCHAR(20) NOT NULL DEFAULT 'calendrier'",
        # Fréquence d'appel du loyer (mensuelle / bimestrielle / trimestrielle / semestrielle / annuelle)
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS payment_frequency VARCHAR(20) NOT NULL DEFAULT 'mensuelle'",
        # Suivi de la relation locataire (scoring)
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS relationship_events JSONB",
        # Révision du loyer (IRL)
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS irl_quarter INTEGER",
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS irl_base_index NUMERIC(8,2)",
        "ALTER TABLE leases ADD COLUMN IF NOT EXISTS last_revision_date DATE",
        # Lien régularisation de charges -> révision de loyer générée (annulation propre)
        "ALTER TABLE charge_regularizations ADD COLUMN IF NOT EXISTS rent_revision_id UUID",
        # Révisions de loyer « par champ » (loyer OU charges). Purge des lignes
        # combinées (schéma initial, données de test) puis bascule du schéma.
        "DELETE FROM lease_rent_revisions",
        "ALTER TABLE lease_rent_revisions DROP COLUMN IF EXISTS rent_amount",
        "ALTER TABLE lease_rent_revisions DROP COLUMN IF EXISTS charges_amount",
        "ALTER TABLE lease_rent_revisions DROP COLUMN IF EXISTS prev_rent_amount",
        "ALTER TABLE lease_rent_revisions DROP COLUMN IF EXISTS prev_charges_amount",
        "ALTER TABLE lease_rent_revisions ADD COLUMN IF NOT EXISTS kind VARCHAR(10) NOT NULL DEFAULT 'rent'",
        "ALTER TABLE lease_rent_revisions ADD COLUMN IF NOT EXISTS amount NUMERIC(10,2) NOT NULL DEFAULT 0",
        "ALTER TABLE lease_rent_revisions ADD COLUMN IF NOT EXISTS prev_amount NUMERIC(10,2)",
        # Période réellement couverte par un avis d'échéance (prorata d'entrée/sortie)
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS period_start DATE",
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS period_end DATE",
        # Période réellement couverte par un loyer (multi-mois selon la fréquence)
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS period_start DATE",
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS period_end DATE",
        # Candidatures : jeton public de dépôt des pièces par le candidat
        "ALTER TABLE candidatures ADD COLUMN IF NOT EXISTS upload_token VARCHAR(64)",
        "CREATE INDEX IF NOT EXISTS ix_candidatures_upload_token ON candidatures (upload_token)",
        # Candidatures : visite (créneau réservé + date d'invitation)
        "ALTER TABLE candidatures ADD COLUMN IF NOT EXISTS visit_slot_id UUID",
        "ALTER TABLE candidatures ADD COLUMN IF NOT EXISTS visit_invited_at TIMESTAMPTZ",
        "ALTER TABLE candidatures ADD COLUMN IF NOT EXISTS visit_reminded_at TIMESTAMPTZ",
        # Identifiant lisible unique (ref_code) : comptes, propriétaires, biens, locataires.
        # Préfixe selon le type/rôle (GM/GP/UP/UL/AD/CB/LE, PR, BN, LO). Reprise
        # historique des lignes existantes au démarrage (voir _backfill_references).
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ref_code VARCHAR(20)",
        "ALTER TABLE owners ADD COLUMN IF NOT EXISTS ref_code VARCHAR(20)",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS ref_code VARCHAR(20)",
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS ref_code VARCHAR(20)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_ref_code ON users (ref_code)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_owners_ref_code ON owners (ref_code)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_tenants_ref_code ON tenants (ref_code)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_properties_ref_code ON properties (ref_code)",
        # Dernière connexion (affichée dans « Gestion des utilisateurs »)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ",
        # Coordonnées profil utilisateur (gestionnaire/agence)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS address VARCHAR(300)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS owner_full_name VARCHAR(150)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_theme VARCHAR(20)",
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
        # NB : les demandes de souscription/démo sont désormais gérées par Alice
        # (base dédiée) via son API /internal ; LeCI ne possède plus de table
        # alice_subscription_requests locale (découplage total).
        # ── Plus de compte « admin » : conversion en Gestionnaire Mandataire ─────
        # L'administration est assurée par Alice. Tout compte encore en rôle 'admin'
        # est converti en 'gestionnaire' (mandataire). Idempotent.
        "UPDATE users SET role = 'gestionnaire' WHERE role = 'admin'",
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
        # Fiche propriétaire : un seul numéro de téléphone → suppression de phone2.
        "ALTER TABLE owners DROP COLUMN IF EXISTS phone2",
        # Adresse propriétaire structurée (rue/CP/ville/pays), comme les biens.
        # `address` reste la rue ; on ajoute CP, ville, pays.
        "ALTER TABLE owners ADD COLUMN IF NOT EXISTS zip_code VARCHAR(20)",
        "ALTER TABLE owners ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
        "ALTER TABLE owners ADD COLUMN IF NOT EXISTS country VARCHAR(80)",
        # Adresse du profil gestionnaire (Mes informations) structurée, idem.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS zip_code VARCHAR(20)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(80)",
        # « Atelier de documents » : variables épinglées par type de document (préférence compte).
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS template_pinned_vars JSONB",
        # Identité du bailleur sur le compte gestionnaire : société/SCI + SIRET/N° pièce.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS owner_company VARCHAR(200)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS owner_national_id VARCHAR(50)",
        # Type d'identité du bailleur : 'personne' / 'societe'. Backfill : 'societe'
        # si une société est déjà renseignée sans nom de personne, sinon 'personne'.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS owner_kind VARCHAR(10) NOT NULL DEFAULT 'personne'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS proprio_visibility JSONB",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS proprio_visibility_default JSONB",
        # Signature numérique du gestionnaire (data-URL PNG) apposée sur les documents.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS signature TEXT",
        # Source de la signature (rééditable) : mode + texte + police saisis.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS signature_mode VARCHAR(16)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS signature_text TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS signature_font VARCHAR(64)",
        # Mot de passe temporaire : forcer le changement à la 1re connexion.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE",
        # ── Paiement en ligne par carte (config propre au gestionnaire) ─────────
        # Clés Stripe/SumUp saisies par le gestionnaire ; secrets stockés chiffrés.
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS card_payments_enabled BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(10)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_secret_key_enc TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_publishable_key VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_webhook_secret_enc TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS sumup_api_key_enc TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS sumup_merchant_code VARCHAR(50)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS payment_currency VARCHAR(3) NOT NULL DEFAULT 'EUR'",
        # Automatisation : clé d'idempotence des envois (anti-doublon).
        "ALTER TABLE communication_logs ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(200)",
        "CREATE INDEX IF NOT EXISTS ix_communication_logs_dedup_key ON communication_logs (dedup_key)",
        # Automatisation : CC (gestionnaire) par règle.
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS cc_emails VARCHAR(500)",
        # Planification : heure d'exécution quotidienne + horodatage de dernière exécution.
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS run_hour INTEGER DEFAULT 8",
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS run_minute INTEGER DEFAULT 0",
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ",
        # Options d'automatisation par règle (générer / déposer / e-mail / SMS).
        # Colonnes ajoutées en NULL puis backfillées UNE SEULE FOIS depuis « channel »
        # (le WHERE ... IS NULL ne matche plus aux boots suivants → aucun écrasement
        # des interrupteurs réglés ensuite par le gestionnaire).
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS auto_generate BOOLEAN",
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS auto_deposit BOOLEAN",
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS send_email BOOLEAN",
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS send_sms BOOLEAN",
        "UPDATE automation_rules SET auto_generate = TRUE WHERE auto_generate IS NULL",
        "UPDATE automation_rules SET auto_deposit = TRUE WHERE auto_deposit IS NULL",
        "UPDATE automation_rules SET send_email = (channel IN ('email','email_sms')) WHERE send_email IS NULL",
        "UPDATE automation_rules SET send_sms = (channel IN ('sms','email_sms')) WHERE send_sms IS NULL",
        "ALTER TABLE automation_rules ALTER COLUMN auto_generate SET DEFAULT TRUE",
        "ALTER TABLE automation_rules ALTER COLUMN auto_deposit SET DEFAULT TRUE",
        "ALTER TABLE automation_rules ALTER COLUMN send_email SET DEFAULT TRUE",
        "ALTER TABLE automation_rules ALTER COLUMN send_sms SET DEFAULT FALSE",
        # Langue préférée du locataire (courriers automatiques multilingues).
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS language VARCHAR(8) DEFAULT 'fr'",
        # Initialise le CC des règles existantes avec l'e-mail du gestionnaire
        # créateur (une seule fois : ne touche que les NULL ; un CC vidé = '').
        "UPDATE automation_rules SET cc_emails = (SELECT email FROM users WHERE users.id = automation_rules.created_by) "
        "WHERE cc_emails IS NULL AND created_by IS NOT NULL",
        # Automatisation : signature (service) par règle + backfill par type
        # (contentieux pour rappels/relances, gestion locative pour le reste).
        "ALTER TABLE automation_rules ADD COLUMN IF NOT EXISTS signature VARCHAR(150)",
        "UPDATE automation_rules SET signature = 'Service contentieux' "
        "WHERE signature IS NULL AND rule_type IN ('rappel_impaye','relance_1','relance_2')",
        "UPDATE automation_rules SET signature = 'Service Gestion Locative' WHERE signature IS NULL",
        # Mois reporté sur un plan d'apurement (sort des impayés/revenus, restaurable).
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS settled_by_plan BOOLEAN NOT NULL DEFAULT FALSE",
        # Apurement partiel : part du solde reportée sur un plan sans solder tout le mois
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount_on_plan NUMERIC(10,2) NOT NULL DEFAULT 0",
        # Avis d'échéance d'apurement : type + lien plan/échéance. L'unicité loyer
        # devient un index partiel (kind='loyer') pour laisser coexister les avis
        # d'apurement sur une même période.
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS kind VARCHAR(16) NOT NULL DEFAULT 'loyer'",
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS plan_id UUID",
        "ALTER TABLE avis_echeances ADD COLUMN IF NOT EXISTS installment_seq INTEGER",
        "ALTER TABLE avis_echeances DROP CONSTRAINT IF EXISTS uq_avis_lease_period",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_avis_loyer_period ON avis_echeances (lease_id, period_year, period_month) WHERE kind = 'loyer'",
        # Locataire personne morale : raison sociale + SIREN/SIRET (national_id reste le NIR).
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS company_name VARCHAR(200)",
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS siret VARCHAR(50)",
        # Reprise des fiches société déjà saisies avant la séparation : le SIREN/SIRET
        # avait été stocké dans national_id ; on le déplace vers siret et on vide le NIR.
        "UPDATE tenants SET siret=national_id, national_id=NULL WHERE COALESCE(company_name,'')<>'' AND COALESCE(siret,'')='' AND COALESCE(national_id,'')<>''",
        "UPDATE users SET owner_kind='societe' WHERE owner_kind='personne' AND COALESCE(owner_company,'')<>'' AND COALESCE(owner_full_name,'')=''",
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
        # Complément d'adresse du bien (ligne 1 des documents : « APPART 11 »…)
        "ALTER TABLE properties ADD COLUMN IF NOT EXISTS address2 VARCHAR(200)",
        # ── Éditeur « Atelier de documents » par blocs (avis d'échéance, mise en page moderne) ────
        "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS blocks JSONB",
        "ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS theme JSONB",
        # Logo du gestionnaire (profil « Mes informations »)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS logo_path VARCHAR(500)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)",
        # ── Actions des agents IA : action en attente de confirmation ───────────
        "ALTER TABLE telegram_links ADD COLUMN IF NOT EXISTS pending_action JSONB",
        "ALTER TABLE telegram_links ADD COLUMN IF NOT EXISTS pending_action_at TIMESTAMPTZ",
        # ── Correctif isolation cloche : purge des notifications « broadcast » ───
        # Les alertes (loyer en retard / bail expirant) étaient créées avec
        # user_id = NULL et la requête les diffusait à TOUS les comptes. Le code
        # cible désormais les bons destinataires ; on supprime les anciennes
        # notifications non ciblées (elles seront régénérées proprement).
        "DELETE FROM notifications WHERE user_id IS NULL",
        # ── Isolation multi-agences : users.agency_id = racine de la chaîne created_by ──
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS agency_id UUID",
        "CREATE INDEX IF NOT EXISTS ix_users_agency_id ON users (agency_id)",
        # Backfill : remonte chaque utilisateur jusqu'à son compte principal (created_by IS NULL).
        # Idempotent (recalcule à chaque démarrage). Les sous-comptes héritent de l'id du principal.
        """
        WITH RECURSIVE chain AS (
            SELECT id, created_by, id AS root FROM users WHERE created_by IS NULL
            UNION ALL
            SELECT u.id, u.created_by, c.root
            FROM users u JOIN chain c ON u.created_by = c.id
        )
        UPDATE users SET agency_id = chain.root FROM chain WHERE users.id = chain.id
        """,
        # Orphelins (created_by cassé/cyclique) → leur propre agence.
        "UPDATE users SET agency_id = id WHERE agency_id IS NULL",
        # ── Index de performance sur les clés étrangères « chaudes » ─────────────
        # PostgreSQL n'indexe PAS automatiquement les FK. Ces colonnes servent de
        # filtre dans la quasi-totalité des listes (par bail, bien, locataire,
        # propriétaire, créateur) → index B-tree pour éviter les seq scans.
        "CREATE INDEX IF NOT EXISTS ix_properties_owner_id ON properties (owner_id)",
        "CREATE INDEX IF NOT EXISTS ix_properties_owner_user_id ON properties (owner_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_properties_created_by ON properties (created_by)",
        "CREATE INDEX IF NOT EXISTS ix_leases_property_id ON leases (property_id)",
        "CREATE INDEX IF NOT EXISTS ix_leases_tenant_id ON leases (tenant_id)",
        "CREATE INDEX IF NOT EXISTS ix_leases_created_by ON leases (created_by)",
        "CREATE INDEX IF NOT EXISTS ix_payments_lease_id ON payments (lease_id)",
        "CREATE INDEX IF NOT EXISTS ix_payments_tenant_id ON payments (tenant_id)",
        # NB : avis_echeances.lease_id/tenant_id déjà indexés par le modèle (index=True).
        "CREATE INDEX IF NOT EXISTS ix_tenants_created_by ON tenants (created_by)",
        "CREATE INDEX IF NOT EXISTS ix_tenants_user_id ON tenants (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_owners_created_by ON owners (created_by)",
        "CREATE INDEX IF NOT EXISTS ix_owners_user_id ON owners (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_contacts_created_by ON contacts (created_by)",
        "CREATE INDEX IF NOT EXISTS ix_lease_tenants_tenant_id ON lease_tenants (tenant_id)",
        "CREATE INDEX IF NOT EXISTS ix_tickets_lease_id ON tickets (lease_id)",
        "CREATE INDEX IF NOT EXISTS ix_inspections_lease_id ON inspections (lease_id)",
        "CREATE INDEX IF NOT EXISTS ix_inspections_property_id ON inspections (property_id)",
        "CREATE INDEX IF NOT EXISTS ix_entretiens_prestataire_id ON entretiens (prestataire_id)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id)",
        # NB : payments & avis_echeances ont déjà une UNIQUE(lease_id, period_year,
        # period_month) → l'index couvrant ce pattern existe déjà (pas de doublon).
        # Liste des notifications d'un utilisateur, non lues d'abord, plus récentes en tête.
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_read_created ON notifications (user_id, is_read, created_at DESC)",
    ]
    try:
        async with engine.begin() as conn:
            # (Sérialisation assurée par le verrou d'init global au démarrage.)
            for sql in migrations:
                await conn.execute(text(sql))
        logger.info("Migrations colonnes appliquées ✓")
    except Exception as exc:
        logger.warning(f"Migration colonnes ignorée (non bloquant) : {exc}")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API de gestion locative : LeComptoirImmo",
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

# Contrat interne unifié /internal (privé, hors /api → non exposé par nginx) ─────
from app.api.v1.internal_admin import router as internal_admin_router  # noqa: E402

app.include_router(internal_admin_router)

# ── Fichiers statiques (logos uploadés) ───────────────────────────────────────
os.makedirs("uploads/logos", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de vérification de santé — utilisé par Docker et le load balancer."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
