from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserAdmin(BaseUserAdmin):
    list_display = ('uuid', 'username', 'first_name',
                    'last_name', 'email', 'is_staff', 'is_active', 'role', 'account_type')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active', 'role', 'account_type')
    ordering = ('-date_joined',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Loud Fits', {'fields': ('role', 'account_type', 'google_id')}),
    )


admin.site.register(User, UserAdmin)
