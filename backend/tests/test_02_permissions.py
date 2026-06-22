"""
Tests unitaires purs — RBAC (sans base de données).
"""

import pytest

from app.core.permissions import ROLE_HIERARCHY, Role, is_manager, role_has_permission


class TestRoleHierarchy:
    def test_admin_has_all_roles(self):
        for role in Role:
            assert role_has_permission(Role.ADMIN, role), f"Admin should have {role}"

    def test_gestionnaire_has_gestionnaire(self):
        assert role_has_permission(Role.GESTIONNAIRE, Role.GESTIONNAIRE)

    def test_gestionnaire_has_lecture(self):
        assert role_has_permission(Role.GESTIONNAIRE, Role.LECTURE)

    def test_gestionnaire_has_locataire(self):
        assert role_has_permission(Role.GESTIONNAIRE, Role.LOCATAIRE)

    def test_gestionnaire_not_admin(self):
        assert not role_has_permission(Role.GESTIONNAIRE, Role.ADMIN)

    def test_locataire_only_locataire(self):
        assert role_has_permission(Role.LOCATAIRE, Role.LOCATAIRE)
        assert not role_has_permission(Role.LOCATAIRE, Role.GESTIONNAIRE)
        assert not role_has_permission(Role.LOCATAIRE, Role.ADMIN)
        assert not role_has_permission(Role.LOCATAIRE, Role.LECTURE)
        assert not role_has_permission(Role.LOCATAIRE, Role.COMPTABLE)

    def test_proprietaire_only_proprietaire(self):
        assert role_has_permission(Role.PROPRIETAIRE, Role.PROPRIETAIRE)
        assert not role_has_permission(Role.PROPRIETAIRE, Role.GESTIONNAIRE)
        assert not role_has_permission(Role.PROPRIETAIRE, Role.ADMIN)

    def test_comptable_has_lecture(self):
        # Le Comptable a le périmètre de LECTURE du gestionnaire (il voit tout) :
        # la hiérarchie inclut volontairement GESTIONNAIRE pour les endpoints en
        # lecture. Ses ÉCRITURES sont restreintes par le garde
        # `enforce_comptable_readonly` (app/api/deps.py), pas par la hiérarchie.
        assert role_has_permission(Role.COMPTABLE, Role.LECTURE)
        assert role_has_permission(Role.COMPTABLE, Role.COMPTABLE)
        assert role_has_permission(Role.COMPTABLE, Role.GESTIONNAIRE)  # lecture étendue
        # Mais ce n'est PAS un gestionnaire complet (pas le panneau de gestion).
        assert not is_manager(Role.COMPTABLE)

    def test_lecture_only_lecture(self):
        assert role_has_permission(Role.LECTURE, Role.LECTURE)
        assert not role_has_permission(Role.LECTURE, Role.COMPTABLE)
        assert not role_has_permission(Role.LECTURE, Role.GESTIONNAIRE)

    def test_all_roles_defined_in_hierarchy(self):
        for role in Role:
            assert role in ROLE_HIERARCHY, f"{role} missing from ROLE_HIERARCHY"

    def test_role_string_values(self):
        assert Role.ADMIN.value == "admin"
        assert Role.GESTIONNAIRE.value == "gestionnaire"
        assert Role.PROPRIETAIRE.value == "proprietaire"
        assert Role.LOCATAIRE.value == "locataire"
        assert Role.LECTURE.value == "lecture"
        assert Role.COMPTABLE.value == "comptable"
