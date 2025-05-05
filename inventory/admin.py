from django.contrib import admin
from .models import Product, Category, Supplier, StockRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone')
    search_fields = ('name', 'contact_person', 'email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'supplier', 'quantity', 'price', 'updated_at')
    list_filter = ('category', 'supplier')
    search_fields = ('name', 'sku', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StockRequest)
class StockRequestAdmin(admin.ModelAdmin):
    list_display = ('product', 'employee', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('product__name', 'employee__username')
    readonly_fields = ('created_at',)
