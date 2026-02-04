from django.contrib import admin
from .models import User

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'username', 'first_name',
                    'last_name',  'email', 'is_staff', 'is_active', 'role', 'account_type')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active', 'role', 'account_type')


admin.site.register(User, UserAdmin)
