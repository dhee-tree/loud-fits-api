from django.contrib import admin
from .models import Order, OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'user', 'status', 'total', 'currency', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('user__email', 'user__username')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'order', 'product_name', 'store_name', 'quantity', 'price_at_purchase', 'store_status')
    list_filter = ('store_status', 'currency')
    search_fields = ('product_name', 'store_name', 'order__user__email')
