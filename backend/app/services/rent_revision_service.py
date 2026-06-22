import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lease import Lease
from app.models.rent_revision import RentRevision


def first_of_next_month(d: date | None = None) -> date:
    """1er jour du mois qui suit `d` (par défaut aujourd'hui). Date d'effet par
    défaut d'une révision : jamais le mois en cours."""
    d = d or date.today()
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


class RentRevisionService:
    """Révisions de loyer/charges « par champ » avec date d'effet (point d'entrée
    unique : édition manuelle, IRL, régularisation de charges, amiable)."""

    @staticmethod
    async def list_for_lease(db: AsyncSession, lease_id: uuid.UUID) -> list[RentRevision]:
        rows = (
            (
                await db.execute(
                    select(RentRevision)
                    .where(RentRevision.lease_id == lease_id)
                    .order_by(RentRevision.effective_date.desc(), RentRevision.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    @staticmethod
    def _effective_field(
        base_value: float, revisions: list[RentRevision], kind: str, on_date: date
    ) -> float:
        """Montant applicable d'un champ à `on_date` = dernière révision de ce champ
        dont la date d'effet précède (ou égale) `on_date` ; sinon `base_value`."""
        rows = [r for r in revisions if r.kind == kind and r.effective_date <= on_date]
        if rows:
            best = max(rows, key=lambda r: (r.effective_date, r.created_at or datetime.min))
            return float(best.amount)
        return float(base_value)

    @staticmethod
    def effective_amounts(
        lease: Lease, revisions: list[RentRevision], on_date: date
    ) -> tuple[float, float]:
        """(loyer, charges) applicables à `on_date`, chaque champ indépendamment."""
        rent = RentRevisionService._effective_field(lease.rent_amount, revisions, "rent", on_date)
        charges = RentRevisionService._effective_field(
            lease.charges_amount, revisions, "charges", on_date
        )
        return rent, charges

    @staticmethod
    async def schedule(
        db: AsyncSession,
        lease: Lease,
        *,
        kind: str,  # 'rent' | 'charges'
        new_amount: float,
        effective_date: date,
        source: str,
        reason: str | None = None,
        created_by: uuid.UUID | None = None,
        notify: bool = True,
    ) -> RentRevision:
        """Programme la révision d'UN champ. S'il existe déjà une révision de ce
        champ non encore appliquée, elle est REMPLACÉE (pas de doublon). On ne
        conserve qu'une révision par champ (la plus récente). Si la date d'effet
        est atteinte, le bail est mis à jour immédiatement."""
        today = date.today()
        # Montant actuellement en vigueur (= « ancien » pour la notification locataire).
        old_for_email = float(lease.rent_amount if kind == "rent" else lease.charges_amount)
        revisions = await RentRevisionService.list_for_lease(db, lease.id)
        same = [r for r in revisions if r.kind == kind]
        pending = next((r for r in same if (not r.applied) and r.effective_date > today), None)
        new_amount = round(float(new_amount), 2)

        if pending:
            # Remplace la révision programmée (prev_amount inchangé : valeur d'avant).
            pending.amount = new_amount
            pending.effective_date = effective_date
            pending.source = source
            pending.reason = reason
            pending.applied = effective_date <= today
            rev = pending
        else:
            base = lease.rent_amount if kind == "rent" else lease.charges_amount
            prev = RentRevisionService._effective_field(base, revisions, kind, today)
            rev = RentRevision(
                lease_id=lease.id,
                kind=kind,
                amount=new_amount,
                prev_amount=round(prev, 2),
                effective_date=effective_date,
                source=source,
                reason=reason,
                created_by=created_by,
                applied=effective_date <= today,
            )
            db.add(rev)
            await db.flush()
            # On ne garde qu'UNE révision par champ : purge des anciennes.
            for r in same:
                if r.id != rev.id:
                    await db.delete(r)

        if effective_date <= today:
            if kind == "rent":
                lease.rent_amount = new_amount
            else:
                lease.charges_amount = new_amount
        await db.flush()
        # Notification e-mail au locataire (si la règle « révision loyer/charges »
        # du gestionnaire est active). Best-effort : n'échoue jamais la révision.
        # `notify=False` quand l'appelant gère lui-même l'e-mail (ex. régularisation
        # de charges qui joint son décompte) afin d'éviter un doublon.
        if notify and round(old_for_email, 2) != new_amount:
            # Avis de révision IRL en pièce jointe (le seul document propre à une
            # révision de loyer) ; révision manuelle/amiable : e-mail sans PJ.
            pdf_bytes = pdf_name = None
            if kind == "rent" and source == "irl":
                try:
                    from app.services.document_blocks_pdf_service import RevisionLoyerPDFService
                    from app.utils.filename import simple_doc_filename

                    pdf_bytes = await RevisionLoyerPDFService.generate(db, lease)
                    pdf_name = simple_doc_filename("revision-loyer", lease.id)
                except Exception:  # noqa: BLE001
                    import logging

                    logging.getLogger(__name__).warning(
                        "[revision] PDF IRL indisponible", exc_info=True
                    )
            try:
                from app.services.automation_engine import send_revision_email

                await send_revision_email(
                    db,
                    lease,
                    kind=kind,
                    old_amount=old_for_email,
                    new_amount=new_amount,
                    effective_date=effective_date,
                    pdf_bytes=pdf_bytes,
                    pdf_name=pdf_name,
                )
            except Exception:  # noqa: BLE001
                import logging

                logging.getLogger(__name__).warning(
                    "[revision] e-mail locataire non envoyé", exc_info=True
                )
        return rev

    @staticmethod
    async def sync_lease_current(db: AsyncSession, lease: Lease) -> bool:
        """Bascule lease.rent_amount/charges_amount sur les montants en vigueur
        aujourd'hui (applique les révisions arrivées à échéance)."""
        revisions = await RentRevisionService.list_for_lease(db, lease.id)
        if not revisions:
            return False
        rent, charges = RentRevisionService.effective_amounts(lease, revisions, date.today())
        changed = False
        if round(float(lease.rent_amount), 2) != round(rent, 2):
            lease.rent_amount = round(rent, 2)
            changed = True
        if round(float(lease.charges_amount), 2) != round(charges, 2):
            lease.charges_amount = round(charges, 2)
            changed = True
        for r in revisions:
            if not r.applied and r.effective_date <= date.today():
                r.applied = True
                changed = True
        if changed:
            await db.flush()
        return changed
