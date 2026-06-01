from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class AliceFeatureRegistry(Base):
    """Registre (ligne unique, id=1) des clés de fonctionnalités déjà connues.

    Permet de détecter au démarrage les NOUVELLES clés du catalogue et de les
    propager (cochées) aux plans existants, sans réactiver celles que l'admin
    a volontairement décochées."""
    __tablename__ = "alice_feature_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    known_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
