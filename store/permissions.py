from rest_framework import permissions
from user.models import User


class IsStoreOwner(permissions.BasePermission):
    """
    Permission class that only allows authenticated users with account_type='Store'
    who own a store to access the view.
    """
    message = "You must be a store owner to access this resource."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.account_type != User.AccountType.STORE:
            return False

        # Check that the user has an associated store
        return hasattr(request.user, 'store')
