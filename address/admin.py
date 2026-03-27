from django.contrib import admin
from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user', 'label', 'city', 'postcode', 'country', 'is_default')
    list_filter = ('is_default', 'country', 'city')
    search_fields = ('user__email', 'user__username', 'label', 'city', 'postcode')
