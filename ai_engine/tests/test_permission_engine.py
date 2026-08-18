import unittest
from uuid import uuid4


class PermissionModelTests(unittest.TestCase):

    def test_permission_stores_resource_and_action(self):
        from ai_engine.app.permissions import Permission

        permission = Permission(
            resource="customer",
            action="read",
        )

        self.assertEqual(
            permission.resource,
            "customer",
        )
        self.assertEqual(
            permission.action,
            "read",
        )

    def test_permission_has_combined_name(self):
        from ai_engine.app.permissions import Permission

        permission = Permission(
            resource="customer",
            action="delete",
        )

        self.assertEqual(
            permission.name,
            "customer.delete",
        )


class RoleTests(unittest.TestCase):

    def test_role_stores_name_and_permissions(self):
        from ai_engine.app.permissions import (
            Permission,
            Role,
        )

        permission = Permission(
            resource="customer",
            action="read",
        )

        role = Role(
            name="support",
            permissions=(permission,),
        )

        self.assertEqual(
            role.name,
            "support",
        )
        self.assertEqual(
            role.permissions,
            (permission,),
        )

    def test_role_defaults_to_no_permissions(self):
        from ai_engine.app.permissions import Role

        role = Role(
            name="viewer",
        )

        self.assertEqual(
            role.permissions,
            (),
        )


class AuthorizationContextTests(unittest.TestCase):

    def test_context_stores_authorization_data(self):
        from ai_engine.app.permissions import (
            AuthorizationContext,
            Role,
        )

        user_id = uuid4()
        organization_id = uuid4()

        role = Role(
            name="admin",
        )

        context = AuthorizationContext(
            user_id=user_id,
            organization_id=organization_id,
            roles=(role,),
            agent_name="operations_agent",
        )

        self.assertEqual(
            context.user_id,
            user_id,
        )
        self.assertEqual(
            context.organization_id,
            organization_id,
        )
        self.assertEqual(
            context.roles,
            (role,),
        )
        self.assertEqual(
            context.agent_name,
            "operations_agent",
        )


class PermissionEngineTests(unittest.TestCase):

    def test_allows_permission_granted_by_role(self):
        from ai_engine.app.permissions import (
            AuthorizationContext,
            Permission,
            PermissionEngine,
            Role,
        )

        permission = Permission(
            resource="customer",
            action="read",
        )

        context = AuthorizationContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            roles=(
                Role(
                    name="support",
                    permissions=(permission,),
                ),
            ),
            agent_name="operations_agent",
        )

        engine = PermissionEngine()

        engine.authorize(
            context=context,
            permission=permission,
        )

    def test_rejects_missing_permission(self):
        from ai_engine.app.permissions import (
            AuthorizationContext,
            Permission,
            PermissionDeniedError,
            PermissionEngine,
            Role,
        )

        granted_permission = Permission(
            resource="customer",
            action="read",
        )

        required_permission = Permission(
            resource="customer",
            action="delete",
        )

        context = AuthorizationContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            roles=(
                Role(
                    name="support",
                    permissions=(granted_permission,),
                ),
            ),
            agent_name="operations_agent",
        )

        engine = PermissionEngine()

        with self.assertRaisesRegex(
            PermissionDeniedError,
            "Permission denied: customer.delete",
        ):
            engine.authorize(
                context=context,
                permission=required_permission,
            )

    def test_allows_permission_from_any_assigned_role(self):
        from ai_engine.app.permissions import (
            AuthorizationContext,
            Permission,
            PermissionEngine,
            Role,
        )

        read_permission = Permission(
            resource="customer",
            action="read",
        )

        delete_permission = Permission(
            resource="customer",
            action="delete",
        )

        context = AuthorizationContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            roles=(
                Role(
                    name="viewer",
                    permissions=(read_permission,),
                ),
                Role(
                    name="admin",
                    permissions=(delete_permission,),
                ),
            ),
            agent_name="operations_agent",
        )

        engine = PermissionEngine()

        engine.authorize(
            context=context,
            permission=delete_permission,
        )

    def test_rejects_when_user_has_no_roles(self):
        from ai_engine.app.permissions import (
            AuthorizationContext,
            Permission,
            PermissionDeniedError,
            PermissionEngine,
        )

        permission = Permission(
            resource="customer",
            action="read",
        )

        context = AuthorizationContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            roles=(),
            agent_name="operations_agent",
        )

        engine = PermissionEngine()

        with self.assertRaisesRegex(
            PermissionDeniedError,
            "Permission denied: customer.read",
        ):
            engine.authorize(
                context=context,
                permission=permission,
            )


if __name__ == "__main__":
    unittest.main()