from django.contrib import admin

from .models import Outfit, OutfitItem


@admin.register(Outfit)
class OutfitAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'owner', 'status', 'is_hidden', 'updated_at')
    search_fields = ('owner__email', 'title')
    list_filter = ('status', 'is_hidden')


@admin.register(OutfitItem)
class OutfitItemAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'outfit', 'slot', 'product_name', 'updated_at')
    search_fields = ('product_name', 'outfit__owner__email')
    list_filter = ('slot',)
