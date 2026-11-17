"""
Django admin customization.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from core import models
from core.services.notifications import post_payload, schedule_push_event


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""

    ordering = ['id']
    list_display = ['email', 'name']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('name', 'foto', 'gang', 'country', 'role')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                )
            },
        ),
        (_('Important dates'), {'fields': ('last_login',)}),
        (_('Groups'), {'fields': ('groups',)}),
        (_('User Permissions'), {'fields': ('user_permissions',)}),
    )
    readonly_fields = ['last_login']
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'password1',
                    'password2',
                    'name',
                    'foto',
                    'gang',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'country',
                    'role'
                ),
            },
        ),
    )


class PostAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            schedule_push_event(post_payload(obj), excluded_endpoint=request.headers.get('X-Push-Endpoint'))


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Task)
admin.site.register(models.Category)
admin.site.register(models.Post, PostAdmin)
admin.site.register(models.Gang)
admin.site.register(models.Country)
admin.site.register(models.Schedule)
admin.site.register(models.Link)
admin.site.register(models.Message)
