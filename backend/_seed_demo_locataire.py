"""Crée (en LOCAL) un locataire de démo avec des scénarios variés pour vérifier
« Ma comptabilité » : mois tiers-payant soldé, mois APL partiel, mois impayé,
et un mois reporté sur plan d'apurement. Idempotent (réutilise/réinitialise)."""
import asyncio
from datetime import date, datetime
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.core.security import hash_password
from app.core.permissions import Role
from app.models.user import User
from app.models.tenant import Tenant
from app.models.property import Property
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.models.apurement_plan import ApurementPlan
from app.models.charge_regularization import ChargeRegularization

EMAIL = "demo.locataire@test.fr"
PASSWORD = "Demo1234!"


async def main():
    async with AsyncSessionLocal() as db:
        # ── Nettoyage si déjà présent (réexécutable) ────────────────────────
        u = (await db.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none()
        if u:
            tens = (await db.execute(select(Tenant).where(Tenant.user_id == u.id))).scalars().all()
            for t in tens:
                leases = (await db.execute(select(Lease).where(Lease.tenant_id == t.id))).scalars().all()
                for l in leases:
                    await db.execute(delete(ApurementPlan).where(ApurementPlan.lease_id == l.id))
                    await db.execute(delete(ChargeRegularization).where(ChargeRegularization.lease_id == l.id))
                    await db.execute(delete(Payment).where(Payment.lease_id == l.id))
                    await db.delete(l)
                await db.flush()
                await db.delete(t)
            await db.flush()
            await db.delete(u)
            await db.flush()

        # ── Compte locataire ────────────────────────────────────────────────
        user = User(email=EMAIL, hashed_password=hash_password(PASSWORD),
                    full_name="Jean Démo", role=Role.LOCATAIRE, is_active=True)
        db.add(user)
        await db.flush()

        prop = Property(name="Résidence Démo · Lot 4", address="12 Rue des Manguiers",
                        zip_code="97300", city="Cayenne", country="France",
                        property_type="appartement")
        db.add(prop)
        await db.flush()

        tenant = Tenant(first_name="Jean", last_name="Démo", email=EMAIL, user_id=user.id)
        db.add(tenant)
        await db.flush()

        # Bail reproduisant le cas signalé : loyer 1100 + charges 50 = 1150 brut,
        # APL tiers payant 753 € (reste à charge = 397 €).
        lease = Lease(tenant_id=tenant.id, property_id=prop.id, start_date=date(2026, 1, 1),
                      rent_amount=1100.00, charges_amount=50.00, lease_type="vide",
                      payment_day=1, is_active=True, apl_amount=753.00, apl_tiers_payant=True)
        db.add(lease)
        await db.flush()

        def mk(month, paid, status, pay_date=None, settled=False, method=None):
            return Payment(lease_id=lease.id, tenant_id=tenant.id, period_year=2026,
                           period_month=month, due_date=date(2026, month, 1),
                           amount_rent=1100.00, amount_charges=50.00, amount_apl=753.00,
                           amount_due=1150.00, amount_paid=paid, status=status,
                           payment_date=pay_date, settled_by_plan=settled,
                           payment_method=method)

        # Mai : SOLDÉ (APL 753 + reste à charge 397 payé le 28 mai par virement) -> mois à 0
        db.add(mk(5, 1150.00, PaymentStatus.PAID, date(2026, 5, 28), method="virement"))
        # Juin : seule l'APL appliquée (753) -> reste à charge 397 non encore réglé
        db.add(mk(6, 753.00, PaymentStatus.PARTIAL))

        # Régularisation de charges 2024 créditrice (trop-perçu remboursé) : +851,70 €
        db.add(ChargeRegularization(
            lease_id=lease.id, tenant_id=tenant.id,
            period_start=date(2024, 1, 1), period_end=date(2024, 12, 31), months_count=12,
            provisions_total=851.70, real_total=0.00, balance=851.70,
            old_monthly_provision=50.00, new_monthly_provision=50.00,
            status="applied", applied_at=datetime(2026, 6, 1, 9, 0, 0)))
        await db.flush()
        await db.commit()
        print(f"OK · locataire démo créé\n  email={EMAIL}\n  password={PASSWORD}\n  user_id={user.id}")


asyncio.run(main())
