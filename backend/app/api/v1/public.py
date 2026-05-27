"""
Endpoints publics (sans authentification) — page d'accueil Le Comptoir Immo.

La demande de souscription/démo est enregistrée dans la table partagée
`proxygen_subscription_requests` ; elle est ensuite traitée côté ProxyGen.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/public", tags=["Public"])


class SubscriptionRequestIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None, max_length=2000)


@router.post("/subscription-requests", status_code=201, summary="Demande de souscription / démo")
async def create_subscription_request(
    data: SubscriptionRequestIn,
    db: AsyncSession = Depends(get_db),
):
    """Enregistre une demande publique (à traiter par l'équipe ProxyGen)."""
    await db.execute(
        text(
            "INSERT INTO proxygen_subscription_requests "
            "(id, full_name, email, phone, company, message, source, status, created_at) "
            "VALUES (:id, :full_name, :email, :phone, :company, :message, "
            "'site_lecomptoir', 'nouveau', now())"
        ),
        {
            "id": uuid.uuid4(),
            "full_name": data.full_name.strip(),
            "email": str(data.email).lower(),
            "phone": data.phone,
            "company": data.company,
            "message": data.message,
        },
    )
    await db.commit()
    return {"status": "received"}
