from django.contrib import admin
from .models import Cart, CartItem, CartAddEvent


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'cart', 'product', 'quantity', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('product__name', 'cart__user__email')


@admin.register(CartAddEvent)
class CartAddEventAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user', 'outfit', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'outfit__title')
