from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Main inventory views
    path('', views.index, name='index'),
    
    # Product management (Employer)
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Category management
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Supplier management
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    
    # Stock requests
    path('requests/', views.stock_request_list, name='stock_request_list'),
    path('requests/my/', views.my_stock_requests, name='my_requests'),
    path('requests/add/', views.request_stock, name='request_stock'),
    path('requests/<int:pk>/', views.stock_request_detail, name='stock_request_detail'),
    path('requests/<int:pk>/approve/', views.approve_stock_request, name='approve_stock_request'),
    path('requests/<int:pk>/reject/', views.reject_stock_request, name='reject_stock_request'),
    
    # Employee views
    path('stock/', views.view_stock, name='view_stock'),
    
    # Analytics and reporting
    path('analytics/', views.inventory_analytics, name='analytics'),
    path('export/', views.export_inventory, name='export_inventory'),
    path('export/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),
    path('export/excel/', views.export_inventory_excel, name='export_inventory_excel'),
    
    # API endpoints for HTMX
    path('api/product-search/', views.product_search, name='product_search'),
    path('api/low-stock-products/', views.low_stock_products, name='low_stock_products'),
]
