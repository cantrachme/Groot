from .models import AuthorizationContext, Permission


class PermissionDeniedError(PermissionError):
    """Raised when a required permission is not granted."""


class PermissionEngine:
    """Authorizes permissions granted through assigned roles."""

    def authorize(
        self,
        context: AuthorizationContext,
        permission: Permission,
    ) -> None:
        for role in context.roles:
            if permission in role.permissions:
                return

        raise PermissionDeniedError(
            f"Permission denied: {permission.name}",
        )
