"""Client générique vers le contrat interne `/internal` d'un produit.

Permet à Alice de piloter LeCI et Séjour de façon identique (même contrat).
Chaque produit = une base URL + une clé partagée (en-tête X-Internal-Key).
"""
from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import HTTPException

from app.config import get_settings

_TIMEOUT = 15.0


class ProductClient:
    def __init__(self, product: str) -> None:
        cfg = get_settings()
        if product == "sejour":
            self.base = cfg.SEJOUR_URL.rstrip("/")
            self.key = cfg.SEJOUR_INTERNAL_KEY
            self.label = "Séjour"
        elif product == "leci":
            self.base = cfg.LECI_URL.rstrip("/")
            self.key = cfg.INTERNAL_API_KEY
            self.label = "Le Comptoir Immo"
        else:
            raise ValueError(f"Produit inconnu: {product}")
        if not self.key:
            raise HTTPException(
                status_code=503,
                detail=f"Intégration {self.label} non configurée (clé interne absente).",
            )

    async def _request(self, method: str, path: str, json: Any = None) -> Optional[Any]:
        url = f"{self.base}{path}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.request(
                    method, url, json=json, headers={"X-Internal-Key": self.key}
                )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"{self.label} injoignable: {exc}")

        if resp.status_code >= 400:
            detail = f"Erreur {self.label} ({resp.status_code})"
            try:
                body = resp.json()
                if isinstance(body, dict) and body.get("detail"):
                    detail = body["detail"]
            except Exception:
                pass
            raise HTTPException(status_code=resp.status_code, detail=detail)

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ── Contrat /internal ────────────────────────────────────────────────────
    async def list_managers(self) -> list[dict]:
        return await self._request("GET", "/internal/managers") or []

    async def get_manager(self, manager_id: str) -> dict:
        return await self._request("GET", f"/internal/managers/{manager_id}")

    async def manager_properties(self, manager_id: str) -> list[dict]:
        return await self._request("GET", f"/internal/managers/{manager_id}/properties") or []

    async def create_manager(self, data: dict) -> dict:
        return await self._request("POST", "/internal/managers", json=data)

    async def update_manager(self, manager_id: str, data: dict) -> dict:
        return await self._request("PATCH", f"/internal/managers/{manager_id}", json=data)

    async def reset_password(self, manager_id: str, new_password: str) -> None:
        await self._request(
            "POST", f"/internal/managers/{manager_id}/reset-password",
            json={"new_password": new_password},
        )

    async def block(self, manager_id: str) -> dict:
        return await self._request("POST", f"/internal/managers/{manager_id}/block") or {}

    async def unblock(self, manager_id: str, user_ids: list[str]) -> None:
        await self._request(
            "POST", f"/internal/managers/{manager_id}/unblock", json={"user_ids": user_ids}
        )

    async def stats(self) -> dict:
        return await self._request("GET", "/internal/stats") or {}
