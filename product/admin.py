from django.contrib import admin
from .models import Product, ProductImportBatch


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'category',
                    'price', 'currency', 'external_id']
    list_filter = ['category', 'store', 'created_at']
    search_fields = ['name', 'external_id', 'store__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ProductImportBatch)
class ProductImportBatchAdmin(admin.ModelAdmin):
    list_display = ['store', 'uploaded_by', 'created_at',
                    'total', 'imported', 'updated', 'failed']
    list_filter = ['store', 'created_at']
    readonly_fields = ['id', 'created_at']
