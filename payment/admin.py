from django.contrib import admin
from .models import PayoutMethod, StoreBalance, Withdrawal, OrderItemStatusHistory


@admin.register(PayoutMethod)
class PayoutMethodAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'store', 'method_type', 'label', 'is_default', 'created_at')
    list_filter = ('method_type', 'is_default')
    search_fields = ('store__name', 'label', 'account_holder_name')


@admin.register(StoreBalance)
class StoreBalanceAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'store', 'currency', 'updated_at')
    search_fields = ('store__name',)


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'store', 'amount', 'status', 'reference', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('store__name', 'reference')


@admin.register(OrderItemStatusHistory)
class OrderItemStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'order_item', 'status', 'changed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_item__product_name', 'changed_by__email')
