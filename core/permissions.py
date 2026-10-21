from rest_framework.permissions import BasePermission


class IsStudentOrOrganizer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_organizer:
            return True
        return user.is_student and user.country_id is not None