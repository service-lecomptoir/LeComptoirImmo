"""Recette fonctionnelle live (BA) — exécutée contre le backend en cours (localhost:8000).
Sortie compacte dans /tmp/recette.txt : une ligne par cas 'PASS/FAIL <code> <desc>'.
Crée des données de test puis nettoie (DELETE) en fin de parcours.
Routes alignées sur app/api/v1 (révision/charges via /actualisation).
"""
import httpx

BASE = "http://localhost:8000/api/v1"
results = []
created = {"properties": [], "tenants": [], "leases": [], "owners": [], "contacts": [], "irl": []}

ACCOUNTS = {
    "gestionnaire": ("gestionnaire@cabinet.fr", "Gestionnaire1!"),
    "gp": ("gestionnaire-proprio@cabinet.fr", "GestionnaireProprio1!"),
    "proprietaire": ("proprietaire@email.fr", "Proprietaire1!"),
    "locataire": ("locataire@email.fr", "Locataire1!"),
}


def rec(ok, code, desc):
    results.append(("PASS" if ok else "FAIL", code, desc))


def login(client, email, pwd):
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": pwd})
    return r.json().get("access_token") if r.status_code == 200 else None


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def items_of(r):
    if r.status_code != 200:
        return []
    j = r.json()
    return j.get("items", j) if isinstance(j, dict) else j


def main():
    with httpx.Client(timeout=30) as c:
        toks = {}
        for role, (email, pwd) in ACCOUNTS.items():
            t = login(c, email, pwd)
            rec(t is not None, 200 if t else 0, f"AUTH login {role}")
            toks[role] = t

        r = c.post(f"{BASE}/auth/login", json={"email": "gestionnaire@cabinet.fr", "password": "wrong"})
        rec(r.status_code == 401, r.status_code, "AUTH bad password -> 401")
        r = c.post(f"{BASE}/auth/login", json={"email": "nobody@x.fr", "password": "x"})
        rec(r.status_code == 401, r.status_code, "AUTH unknown email -> 401")

        g, gp, prop, loc = toks["gestionnaire"], toks["gp"], toks["proprietaire"], toks["locataire"]

        r = c.get(f"{BASE}/auth/me", headers=H(g))
        rec(r.status_code == 200, r.status_code, "AUTH /me gestionnaire")
        r = c.get(f"{BASE}/auth/me")
        rec(r.status_code in (401, 403), r.status_code, "AUTH /me no token -> 401/403")

        gets = [
            ("/properties", "PROP list"), ("/tenants", "TENANT list"), ("/leases", "LEASE list"),
            ("/payments", "PAY list"), ("/avis-echeances", "AVIS list"),
            ("/notifications", "NOTIF list"), ("/notifications/count", "NOTIF count"),
            ("/documents", "DOC list"), ("/tickets", "TKT list"), ("/contacts", "CONT list"),
            ("/entretiens", "ENT list"), ("/inspections", "INS list"),
            ("/automation/rules", "AUTO rules"), ("/automation/logs", "AUTO logs"),
            ("/dashboard/stats", "DASH stats"), ("/audit", "AUDIT list"),
            ("/owners", "OWNERS list"), ("/subscription", "SUB get"),
            ("/templates", "TPL list"), ("/settings/scheduler", "SET scheduler"),
            ("/actualisation/irl", "IRL list"), ("/actualisation/loyers", "REVISION list"),
            ("/actualisation/charges", "CHARGES list"),
        ]
        for path, desc in gets:
            r = c.get(f"{BASE}{path}", headers=H(g))
            rec(r.status_code == 200, r.status_code, f"{desc} (gestionnaire)")

        # RBAC negatives
        r = c.post(f"{BASE}/tenants", headers=H(loc), json={"first_name": "X", "last_name": "Y", "email": "z@z.fr"})
        rec(r.status_code == 403, r.status_code, "RBAC locataire POST /tenants -> 403")
        r = c.post(f"{BASE}/properties", headers=H(prop), json={"name": "X", "address": "a", "city": "b", "zip_code": "75000", "property_type": "appartement"})
        rec(r.status_code == 403, r.status_code, "RBAC proprietaire POST /properties -> 403")
        r = c.get(f"{BASE}/properties")
        rec(r.status_code in (401, 403), r.status_code, "RBAC no token /properties -> 401/403")
        r = c.get(f"{BASE}/audit", headers=H(loc))
        rec(r.status_code == 403, r.status_code, "RBAC locataire /audit -> 403")
        r = c.get(f"{BASE}/contacts", headers=H(loc))
        rec(r.status_code == 403, r.status_code, "RBAC locataire /contacts -> 403")
        r = c.get(f"{BASE}/tickets", headers=H(loc))
        rec(r.status_code == 403, r.status_code, "RBAC locataire /tickets -> 403")
        r = c.get(f"{BASE}/actualisation/loyers", headers=H(loc))
        rec(r.status_code == 403, r.status_code, "RBAC locataire /actualisation/loyers -> 403")
        r = c.get(f"{BASE}/tickets/mine", headers=H(loc))
        rec(r.status_code == 200, r.status_code, "TKT /tickets/mine (locataire)")

        r = c.get(f"{BASE}/payments/locataire/current", headers=H(loc))
        rec(r.status_code == 200, r.status_code, "PAY locataire current")
        r = c.get(f"{BASE}/leases", headers=H(loc))
        rec(r.status_code == 200, r.status_code, "LEASE list (locataire filtré)")

        r = c.get(f"{BASE}/proprietaire-messages", headers=H(prop))
        rec(r.status_code == 200, r.status_code, "MSG list (proprietaire)")
        r = c.get(f"{BASE}/proprietaire-messages/unread-count", headers=H(prop))
        rec(r.status_code == 200, r.status_code, "MSG unread-count (proprietaire)")
        r = c.get(f"{BASE}/proprietaire-messages", headers=H(loc))
        rec(r.status_code == 403, r.status_code, "MSG list (locataire) -> 403")

        # ── OWNER CRUD ──
        r = c.post(f"{BASE}/owners", headers=H(g), json={"last_name": "RecetteOwner", "email": "recette.owner@test.fr", "phone": "0600000000"})
        owner_id = r.json().get("id") if r.status_code in (200, 201) else None
        if owner_id:
            created["owners"].append(owner_id)
        rec(r.status_code in (200, 201), r.status_code, "OWNER create")
        if owner_id:
            r = c.get(f"{BASE}/owners/{owner_id}", headers=H(g))
            rec(r.status_code == 200, r.status_code, "OWNER get by id")
            r = c.put(f"{BASE}/owners/{owner_id}", headers=H(g), json={"last_name": "RecetteOwnerMod", "iban": "FR7630006000011234567890189", "bic": "AGRIFRPP", "bank_holder": "RecetteOwnerMod"})
            rec(r.status_code == 200, r.status_code, "OWNER update (+RIB)")

        # ── PROPERTY CRUD ──
        pl = {"name": "Recette Bien", "address": "1 rue de Test", "city": "Paris", "zip_code": "75001",
              "property_type": "appartement", "area_sqm": 45.5, "floor": 2, "furnished": True}
        if owner_id:
            pl["owner_id"] = owner_id
        r = c.post(f"{BASE}/properties", headers=H(g), json=pl)
        prop_id = r.json().get("id") if r.status_code in (200, 201) else None
        if prop_id:
            created["properties"].append(prop_id)
        rec(r.status_code in (200, 201), r.status_code, "PROP create")
        if prop_id:
            r = c.get(f"{BASE}/properties/{prop_id}", headers=H(g))
            rec(r.status_code == 200, r.status_code, "PROP get by id")
            r = c.put(f"{BASE}/properties/{prop_id}", headers=H(g), json={"name": "Recette Bien Modifié", "area_sqm": 50})
            rec(r.status_code == 200, r.status_code, "PROP update")

        # ── TENANT CRUD ──
        r = c.post(f"{BASE}/tenants", headers=H(g), json={"first_name": "Jean", "last_name": "RecetteLoc", "email": "recette.loc@test.fr", "phone": "0611111111"})
        tenant_id = r.json().get("id") if r.status_code in (200, 201) else None
        if tenant_id:
            created["tenants"].append(tenant_id)
        rec(r.status_code in (200, 201), r.status_code, "TENANT create")
        if tenant_id:
            r = c.get(f"{BASE}/tenants/{tenant_id}", headers=H(g))
            rec(r.status_code == 200, r.status_code, "TENANT get by id")
            r = c.put(f"{BASE}/tenants/{tenant_id}", headers=H(g), json={"first_name": "Jean-Mod", "last_name": "RecetteLoc", "email": "recette.loc@test.fr"})
            rec(r.status_code == 200, r.status_code, "TENANT update")

        # ── LEASE CRUD + features ──
        lease_id = None
        if prop_id and tenant_id:
            ll = {"property_id": prop_id, "tenant_id": tenant_id, "start_date": "2026-01-01",
                  "rent_amount": 800, "charges_amount": 50, "deposit_amount": 800,
                  "rent_call_rule": "calendrier", "payment_frequency": "mensuelle",
                  "payment_day": 1}
            r = c.post(f"{BASE}/leases", headers=H(g), json=ll)
            lease_id = r.json().get("id") if r.status_code in (200, 201) else None
            if lease_id:
                created["leases"].append(lease_id)
            rec(r.status_code in (200, 201), r.status_code, f"LEASE create (freq+rule) [{r.text[:80] if r.status_code not in (200,201) else ''}]")
        if lease_id:
            r = c.get(f"{BASE}/leases/{lease_id}", headers=H(g))
            rec(r.status_code == 200, r.status_code, "LEASE get by id")

        # ── IRL index + révision (Actualisation étape 1) ──
        r = c.post(f"{BASE}/actualisation/irl", headers=H(g), json={"year": 2024, "quarter": 1, "value": 143.46})
        rec(r.status_code in (200, 201), r.status_code, "IRL upsert index T1-2024")
        r = c.post(f"{BASE}/actualisation/irl", headers=H(g), json={"year": 2025, "quarter": 1, "value": 145.47})
        rec(r.status_code in (200, 201), r.status_code, "IRL upsert index T1-2025")
        # robustesse : trimestre invalide
        r = c.post(f"{BASE}/actualisation/irl", headers=H(g), json={"year": 2025, "quarter": 9, "value": 100})
        rec(r.status_code == 400, r.status_code, "IRL quarter invalide -> 400")
        if lease_id:
            r = c.patch(f"{BASE}/actualisation/loyers/{lease_id}/reference", headers=H(g), json={"irl_quarter": 1, "irl_base_index": 143.46})
            rec(r.status_code == 200, r.status_code, "REVISION set reference")
            r = c.post(f"{BASE}/actualisation/loyers/{lease_id}/appliquer", headers=H(g))
            ok = r.status_code == 200
            new_rent = r.json().get("current_rent") if ok else None
            rec(ok, r.status_code, f"REVISION appliquer (loyer={new_rent})")

        # ── Régularisation charges (Actualisation étape 3) ──
        if lease_id:
            r = c.post(f"{BASE}/actualisation/charges/{lease_id}/preview", headers=H(g),
                       json={"period_start": "2026-01-01", "period_end": "2026-12-31", "real_total": 720})
            rec(r.status_code == 200, r.status_code, "CHARGES preview")
            # robustesse période invalide
            r = c.post(f"{BASE}/actualisation/charges/{lease_id}/preview", headers=H(g),
                       json={"period_start": "2026-12-31", "period_end": "2026-01-01", "real_total": 720})
            rec(r.status_code == 400, r.status_code, "CHARGES preview période invalide -> 400")

        # ── PAYMENTS generation ──
        r = c.post(f"{BASE}/payments/generate", headers=H(g), json={"year": 2026, "month": 1})
        rec(r.status_code in (200, 201), r.status_code, f"PAY generate month [{r.text[:60] if r.status_code not in (200,201) else ''}]")

        # ── CONTACT CRUD ──
        r = c.post(f"{BASE}/contacts", headers=H(g), json={"last_name": "Plombier Recette", "category": "plombier", "phone": "0622222222", "email": "plombier@test.fr"})
        contact_id = r.json().get("id") if r.status_code in (200, 201) else None
        if contact_id:
            created["contacts"].append(contact_id)
        rec(r.status_code in (200, 201), r.status_code, "CONT create")

        # ── ISOLATION GP / mandataire ──
        r = c.post(f"{BASE}/properties", headers=H(gp), json={"name": "Bien GP Recette", "address": "2 rue GP", "city": "Lyon", "zip_code": "69001", "property_type": "appartement"})
        gp_prop_id = r.json().get("id") if r.status_code in (200, 201) else None
        if gp_prop_id:
            created["properties"].append(gp_prop_id)
        rec(r.status_code in (200, 201), r.status_code, "ISO GP create property")
        if gp_prop_id:
            ids = [p.get("id") for p in items_of(c.get(f"{BASE}/properties", headers=H(g)))]
            rec(gp_prop_id not in ids, 200, "ISO mandataire ne voit PAS le bien GP")
            ids = [p.get("id") for p in items_of(c.get(f"{BASE}/properties", headers=H(gp)))]
            rec(gp_prop_id in ids, 200, "ISO GP voit son propre bien")

        r = c.get(f"{BASE}/dashboard/proprietaire-stats", headers=H(prop))
        rec(r.status_code in (200, 404), r.status_code, "DASH proprietaire-stats")

        # ── CLEANUP ──
        if lease_id:
            r = c.delete(f"{BASE}/leases/{lease_id}", headers=H(g))
            rec(r.status_code in (200, 204), r.status_code, "LEASE delete")
        for cid in created["contacts"]:
            r = c.delete(f"{BASE}/contacts/{cid}", headers=H(g))
            rec(r.status_code in (200, 204), r.status_code, "CONT delete")
        for tid in created["tenants"]:
            r = c.delete(f"{BASE}/tenants/{tid}", headers=H(g))
            rec(r.status_code in (200, 204), r.status_code, "TENANT delete")
        for pid in created["properties"]:
            tok = gp if pid == gp_prop_id else g
            r = c.delete(f"{BASE}/properties/{pid}", headers=H(tok))
            rec(r.status_code in (200, 204), r.status_code, "PROP delete")
        for oid in created["owners"]:
            r = c.delete(f"{BASE}/owners/{oid}", headers=H(g))
            rec(r.status_code in (200, 204), r.status_code, "OWNER delete")

    npass = sum(1 for s, _, _ in results if s == "PASS")
    nfail = len(results) - npass
    lines = [f"RECETTE LIVE — {npass} PASS / {nfail} FAIL / {len(results)} total", ""]
    lines += [f"{s} [{code}] {desc}" for s, code, desc in results]
    open("_recette_result.txt", "w", encoding="utf-8").write("\n".join(lines))
    print(f"DONE {npass} PASS {nfail} FAIL")


if __name__ == "__main__":
    main()
