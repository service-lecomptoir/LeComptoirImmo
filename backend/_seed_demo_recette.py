"""Données de DÉMO/RECETTE (LOCAL) pour le compte mandataire gestionnaire@cabinet.fr :
2 propriétaires, 3 biens rattachés, 3 locataires + baux, et des écritures variées
(appels de loyer, règlements, APL, mois impayé). Permet de tester la comptabilité
groupée par propriétaire, les listes, le dashboard et les documents.

Idempotent : nettoie sa propre data (tag) avant de recréer. Local uniquement.
"""
import asyncio
from datetime import date
from sqlalchemy import select, delete

from app.database import AsyncSessionLocal
from app.core.permissions import Role
from app.models.user import User
from app.models.owner import Owner
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus

GEST_EMAIL = "gestionnaire@cabinet.fr"
SEED_TAG = "__seed_recette__"          # marqueur (notes) pour le nettoyage
TENANT_DOMAIN = "@recette.demo"         # emails locataires de la démo

YEAR = 2026


async def main():
    async with AsyncSessionLocal() as db:
        gest = (await db.execute(select(User).where(User.email == GEST_EMAIL))).scalar_one_or_none()
        if not gest:
            print(f"Compte gestionnaire {GEST_EMAIL} introuvable. Abandon.")
            return
        gid = gest.id

        # ── Nettoyage de la data de seed précédente ─────────────────────────
        old_owners = (await db.execute(
            select(Owner).where(Owner.created_by == gid, Owner.notes == SEED_TAG)
        )).scalars().all()
        old_tenants = (await db.execute(
            select(Tenant).where(Tenant.email.like(f"%{TENANT_DOMAIN}"))
        )).scalars().all()
        old_prop_ids = [p.id for p in (await db.execute(
            select(Property).where(Property.owner_id.in_([o.id for o in old_owners]))
        )).scalars().all()] if old_owners else []
        for t in old_tenants:
            for l in (await db.execute(select(Lease).where(Lease.tenant_id == t.id))).scalars().all():
                await db.execute(delete(Payment).where(Payment.lease_id == l.id))
                await db.delete(l)
            await db.flush()
        for pid in old_prop_ids:
            for l in (await db.execute(select(Lease).where(Lease.property_id == pid))).scalars().all():
                await db.execute(delete(Payment).where(Payment.lease_id == l.id))
                await db.delete(l)
        await db.flush()
        for t in old_tenants:
            await db.delete(t)
        for pid in old_prop_ids:
            p = await db.get(Property, pid)
            if p:
                await db.delete(p)
        await db.flush()
        for o in old_owners:
            await db.delete(o)
        await db.flush()

        # ── Propriétaires ───────────────────────────────────────────────────
        owner_dupont = Owner(
            first_name="Pierre", last_name="Dupont", email="pierre.dupont@recette.demo",
            phone="06 11 22 33 44", address="3 rue des Lilas", zip_code="75011", city="Paris",
            country="France", iban="FR7630006000011234567890189", bic="AGRIFRPP",
            bank_holder="Pierre Dupont", created_by=gid, notes=SEED_TAG,
        )
        owner_sci = Owner(
            last_name="SCI Les Tilleuls", company_name="SCI Les Tilleuls",
            national_id="84212345600018", email="contact@tilleuls.recette.demo",
            phone="01 45 67 89 10", address="18 avenue Victor Hugo", zip_code="69006",
            city="Lyon", country="France", iban="FR7630004000031234567890143", bic="BNPAFRPP",
            bank_holder="SCI Les Tilleuls", created_by=gid, notes=SEED_TAG,
        )
        db.add_all([owner_dupont, owner_sci])
        await db.flush()

        # ── Biens (rattachés à un propriétaire) ─────────────────────────────
        def mk_prop(name, addr, zip_, city, owner):
            return Property(
                name=name, address=addr, zip_code=zip_, city=city, country="France",
                property_type="appartement", owner_id=owner.id, owner_name=owner.full_name,
                created_by=gid, is_occupied=True, is_available=False,
            )
        p_villa = mk_prop("Villa Horizon", "12 chemin de la Plage", "06400", "Cannes", owner_dupont)
        p_til_a = mk_prop("Les Tilleuls · A2", "18 avenue Victor Hugo", "69006", "Lyon", owner_sci)
        p_til_b = mk_prop("Les Tilleuls · B5", "18 avenue Victor Hugo", "69006", "Lyon", owner_sci)
        db.add_all([p_villa, p_til_a, p_til_b])
        await db.flush()

        # ── Locataires + baux + écritures ───────────────────────────────────
        def mk_tenant(first, last, email):
            return Tenant(first_name=first, last_name=last, email=email,
                          phone="06 00 00 00 00", created_by=gid)

        def mk_lease(tenant, prop, rent, charges, apl=0.0, tiers=False):
            return Lease(tenant_id=tenant.id, property_id=prop.id, start_date=date(YEAR, 1, 1),
                         rent_amount=rent, charges_amount=charges, lease_type="vide",
                         payment_day=1, is_active=True, created_by=gid,
                         apl_amount=apl, apl_tiers_payant=tiers)

        def mk_pay(lease, tenant, month, rent, charges, apl, paid, status, method=None, pdate=None):
            return Payment(lease_id=lease.id, tenant_id=tenant.id, period_year=YEAR,
                           period_month=month, due_date=date(YEAR, month, 1),
                           amount_rent=rent, amount_charges=charges, amount_apl=apl or None,
                           amount_due=round(rent + charges - (apl or 0), 2),
                           amount_paid=paid, status=status, payment_method=method, payment_date=pdate)

        # 1) Sophie Martin — Villa Horizon (Dupont) : mai soldé, juin partiel
        t1 = mk_tenant("Sophie", "Martin", "sophie.martin@recette.demo"); db.add(t1); await db.flush()
        l1 = mk_lease(t1, p_villa, 950.00, 50.00); db.add(l1); await db.flush()
        db.add(mk_pay(l1, t1, 5, 950, 50, 0, 1000.00, PaymentStatus.PAID, "virement", date(YEAR, 5, 3)))
        db.add(mk_pay(l1, t1, 6, 950, 50, 0, 400.00, PaymentStatus.PARTIAL, "virement", date(YEAR, 6, 5)))

        # 2) Marc Petit — Tilleuls A2 (SCI) : mai et juin soldés (APL tiers payant)
        t2 = mk_tenant("Marc", "Petit", "marc.petit@recette.demo"); db.add(t2); await db.flush()
        l2 = mk_lease(t2, p_til_a, 700.00, 40.00, apl=300.00, tiers=True); db.add(l2); await db.flush()
        db.add(mk_pay(l2, t2, 5, 700, 40, 300, 740.00, PaymentStatus.PAID, "virement", date(YEAR, 5, 2)))
        db.add(mk_pay(l2, t2, 6, 700, 40, 300, 740.00, PaymentStatus.PAID, "prelevement", date(YEAR, 6, 2)))

        # 3) Lina Bernard — Tilleuls B5 (SCI) : juin impayé (en retard)
        t3 = mk_tenant("Lina", "Bernard", "lina.bernard@recette.demo"); db.add(t3); await db.flush()
        l3 = mk_lease(t3, p_til_b, 820.00, 60.00); db.add(l3); await db.flush()
        db.add(mk_pay(l3, t3, 5, 820, 60, 0, 880.00, PaymentStatus.PAID, "virement", date(YEAR, 5, 4)))
        db.add(mk_pay(l3, t3, 6, 820, 60, 0, 0.00, PaymentStatus.LATE))

        await db.flush()
        await db.commit()
        print("OK · données de recette créées pour", GEST_EMAIL)
        print("  Propriétaires : Pierre Dupont (Villa Horizon) · SCI Les Tilleuls (A2, B5)")
        print("  Locataires : Sophie Martin, Marc Petit, Lina Bernard (emails @recette.demo)")


asyncio.run(main())
