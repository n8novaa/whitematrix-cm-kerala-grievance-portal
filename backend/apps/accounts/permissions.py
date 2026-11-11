from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    """Base class for permissions tied to the server-side authenticated role."""
    allowed_roles = ()

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in self.allowed_roles)


class IsCitizen(HasRole):
    allowed_roles = ('CITIZEN',)


class IsCMO(HasRole):
    allowed_roles = ('CMO',)


class IsOfficer(HasRole):
    allowed_roles = ('OFFICER',)


class IsCMOOrOfficer(HasRole):
    allowed_roles = ('CMO', 'OFFICER')
