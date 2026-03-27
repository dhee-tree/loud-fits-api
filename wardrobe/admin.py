from django.contrib import admin
from .models import WardrobeItem


@admin.register(WardrobeItem)
class WardrobeItemAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user', 'product', 'source', 'added_at')
    list_filter = ('source', 'added_at')
    search_fields = ('user__email', 'user__username', 'product__name')
