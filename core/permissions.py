from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and (user.is_superuser or user.is_organizer)


class HasDelegationForWrite(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return user.is_authenticated and (
            user.is_superuser or not user.is_student or user.country_id is not None
        )


class IsOrganizerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return user.is_authenticated and (user.is_superuser or user.is_organizer)


class IsStudentOrOrganizer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_organizer:
            return True
        return user.is_student and user.country_id is not None
