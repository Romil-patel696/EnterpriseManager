from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q, F
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Product, Category, Supplier, StockRequest, InventoryLog
from .forms import ProductForm, CategoryForm, SupplierForm, StockRequestForm
from .filters import ProductFilter
from .utils import generate_inventory_pdf, generate_inventory_excel
from core.models import Notification
from accounts.models import UserProfile
import json
import csv
from datetime import datetime, timedelta

@login_required
def index(request):
    """Inventory module index page"""
    user = request.user
    context = {}
    
    # Stats for both employer and employee
    total_products = Product.objects.count()
    low_stock_count = Product.objects.filter(quantity__lt=F('threshold_quantity')).count()
    
    context.update({
        'total_products': total_products,
        'low_stock_count': low_stock_count,
    })
    
    if user.is_employer:
        # Employer-specific data
        pending_requests = StockRequest.objects.filter(status=StockRequest.PENDING).count()
        total_stock_value = Product.objects.aggregate(
            total_value=Sum(F('price') * F('quantity'))
        )['total_value'] or 0
        
        # Top categories
        top_categories = Category.objects.annotate(
            products_count=Count('products')
        ).order_by('-products_count')[:5]
        
        # Recent inventory logs
        recent_logs = InventoryLog.objects.select_related('product', 'user').order_by('-created_at')[:10]
        
        context.update({
            'is_employer': True,
            'pending_requests': pending_requests,
            'total_stock_value': total_stock_value,
            'top_categories': top_categories,
            'recent_logs': recent_logs,
        })
    else:
        # Employee-specific data
        my_pending_requests = StockRequest.objects.filter(
            employee=user, 
            status=StockRequest.PENDING
        ).count()
        
        my_recent_requests = StockRequest.objects.filter(
            employee=user
        ).select_related('product').order_by('-created_at')[:5]
        
        context.update({
            'is_employee': True,
            'my_pending_requests': my_pending_requests,
            'my_recent_requests': my_recent_requests,
        })
    
    return render(request, 'inventory/index.html', context)

# Product Views
@login_required
def product_list(request):
    """List all products with filters"""
    products = Product.objects.select_related('category', 'supplier').all()
    
    # Apply filters
    product_filter = ProductFilter(request.GET, queryset=products)
    products = product_filter.qs
    
    # Paginate the results
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # For HTMX requests, return only the table body
    if request.headers.get('HX-Request'):
        context = {
            'page_obj': page_obj,
            'product_filter': product_filter,
        }
        return render(request, 'inventory/partials/product_table.html', context)
    
    context = {
        'page_obj': page_obj,
        'product_filter': product_filter,
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, pk):
    """View product details"""
    product = get_object_or_404(Product, pk=pk)
    
    # Get product logs for history
    logs = InventoryLog.objects.filter(product=product).order_by('-created_at')[:10]
    
    # Get pending requests for this product
    pending_requests = StockRequest.objects.filter(
        product=product, 
        status=StockRequest.PENDING
    ).select_related('employee').order_by('-created_at')
    
    context = {
        'product': product,
        'logs': logs,
        'pending_requests': pending_requests,
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def product_create(request):
    """Create a new product"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to add products.")
        return redirect('inventory:index')
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            
            # Create inventory log
            InventoryLog.objects.create(
                product=product,
                user=request.user,
                quantity_change=product.quantity,
                previous_quantity=0,
                new_quantity=product.quantity,
                action=InventoryLog.ADDITION,
                note='Initial product creation'
            )
            
            messages.success(request, f"Product '{product.name}' has been added successfully.")
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm()
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'title': 'Add New Product'
    })

@login_required
def product_update(request, pk):
    """Update an existing product"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to edit products.")
        return redirect('inventory:index')
    
    product = get_object_or_404(Product, pk=pk)
    old_quantity = product.quantity
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            updated_product = form.save()
            
            # Check if quantity changed
            if old_quantity != updated_product.quantity:
                # Create inventory log
                InventoryLog.objects.create(
                    product=updated_product,
                    user=request.user,
                    quantity_change=updated_product.quantity - old_quantity,
                    previous_quantity=old_quantity,
                    new_quantity=updated_product.quantity,
                    action=InventoryLog.ADJUSTMENT,
                    note=f'Manual adjustment during product update'
                )
            
            messages.success(request, f"Product '{updated_product.name}' has been updated successfully.")
            return redirect('inventory:product_detail', pk=updated_product.pk)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'product': product,
        'title': 'Edit Product'
    })

@login_required
def product_delete(request, pk):
    """Delete a product"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to delete products.")
        return redirect('inventory:index')
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f"Product '{product_name}' has been deleted successfully.")
        return redirect('inventory:product_list')
    
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})

# Category Views
@login_required
def category_list(request):
    """List all categories"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to view categories.")
        return redirect('inventory:index')
    
    categories = Category.objects.annotate(products_count=Count('products')).order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    """Create a new category"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to add categories.")
        return redirect('inventory:index')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' has been added successfully.")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'inventory/category_form.html', {
        'form': form,
        'title': 'Add New Category'
    })

@login_required
def category_update(request, pk):
    """Update an existing category"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to edit categories.")
        return redirect('inventory:index')
    
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            updated_category = form.save()
            messages.success(request, f"Category '{updated_category.name}' has been updated successfully.")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'inventory/category_form.html', {
        'form': form,
        'category': category,
        'title': 'Edit Category'
    })

@login_required
def category_delete(request, pk):
    """Delete a category"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to delete categories.")
        return redirect('inventory:index')
    
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        # Check if category has products
        if category.products.exists():
            messages.error(request, f"Cannot delete '{category.name}' as it has products assigned to it.")
            return redirect('inventory:category_list')
        
        category_name = category.name
        category.delete()
        messages.success(request, f"Category '{category_name}' has been deleted successfully.")
        return redirect('inventory:category_list')
    
    return render(request, 'inventory/category_confirm_delete.html', {'category': category})

# Supplier Views
@login_required
def supplier_list(request):
    """List all suppliers"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to view suppliers.")
        return redirect('inventory:index')
    
    suppliers = Supplier.objects.annotate(products_count=Count('products')).order_by('name')
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@login_required
def supplier_detail(request, pk):
    """View supplier details"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to view supplier details.")
        return redirect('inventory:index')
    
    supplier = get_object_or_404(Supplier, pk=pk)
    products = Product.objects.filter(supplier=supplier)
    
    return render(request, 'inventory/supplier_detail.html', {
        'supplier': supplier,
        'products': products
    })

@login_required
def supplier_create(request):
    """Create a new supplier"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to add suppliers.")
        return redirect('inventory:index')
    
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.name}' has been added successfully.")
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'title': 'Add New Supplier'
    })

@login_required
def supplier_update(request, pk):
    """Update an existing supplier"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to edit suppliers.")
        return redirect('inventory:index')
    
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            updated_supplier = form.save()
            messages.success(request, f"Supplier '{updated_supplier.name}' has been updated successfully.")
            return redirect('inventory:supplier_detail', pk=updated_supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': 'Edit Supplier'
    })

@login_required
def supplier_delete(request, pk):
    """Delete a supplier"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to delete suppliers.")
        return redirect('inventory:index')
    
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        # Check if supplier has products
        if supplier.products.exists():
            messages.error(request, f"Cannot delete supplier '{supplier.name}' as it has products assigned to it.")
            return redirect('inventory:supplier_list')
        
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier '{supplier_name}' has been deleted successfully.")
        return redirect('inventory:supplier_list')
    
    return render(request, 'inventory/supplier_confirm_delete.html', {'supplier': supplier})

# Stock Request Views
@login_required
def stock_request_list(request):
    """List all stock requests (for employers)"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to view all stock requests.")
        return redirect('inventory:index')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    
    if status_filter and status_filter in dict(StockRequest.STATUS_CHOICES):
        requests = StockRequest.objects.filter(status=status_filter)
    else:
        requests = StockRequest.objects.all()
    
    # Order by creation date, newest first
    requests = requests.select_related('product', 'employee').order_by('-created_at')
    
    # Paginate the results
    paginator = Paginator(requests, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/stock_request_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': StockRequest.STATUS_CHOICES,
    })

@login_required
def my_stock_requests(request):
    """View employee's own stock requests"""
    requests = StockRequest.objects.filter(
        employee=request.user
    ).select_related('product').order_by('-created_at')
    
    return render(request, 'inventory/my_stock_requests.html', {'requests': requests})

@login_required
def request_stock(request):
    """Create new stock request (for employees)"""
    if request.method == 'POST':
        form = StockRequestForm(request.POST)
        if form.is_valid():
            stock_request = form.save(commit=False)
            stock_request.employee = request.user
            
            # Check if the requested quantity is available
            product = stock_request.product
            if stock_request.quantity > product.quantity:
                messages.error(request, f"Requested quantity exceeds available stock. Available: {product.quantity}")
                return render(request, 'inventory/stock_request_form.html', {'form': form})
            
            stock_request.save()
            
            # Create notification for employers
            employers = UserProfile.objects.filter(role=UserProfile.EMPLOYER).values_list('user', flat=True)
            for employer_id in employers:
                Notification.create_notification(
                    user_id=employer_id,
                    title="New Stock Request",
                    message=f"{request.user.get_full_name()} has requested {stock_request.quantity} units of {product.name}",
                    notification_type=Notification.INVENTORY,
                    link=f"/inventory/requests/{stock_request.id}/"
                )
            
            messages.success(request, "Stock request submitted successfully. Waiting for approval.")
            return redirect('inventory:my_requests')
    else:
        form = StockRequestForm()
    
    return render(request, 'inventory/stock_request_form.html', {'form': form})

@login_required
def stock_request_detail(request, pk):
    """View stock request details"""
    stock_request = get_object_or_404(StockRequest, pk=pk)
    
    # Check if user is authorized to view this request
    if not request.user.is_employer and request.user != stock_request.employee:
        messages.error(request, "You don't have permission to view this stock request.")
        return redirect('inventory:index')
    
    return render(request, 'inventory/stock_request_detail.html', {'request': stock_request})

@login_required
def approve_stock_request(request, pk):
    """Approve a stock request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to approve stock requests.")
        return redirect('inventory:index')
    
    stock_request = get_object_or_404(StockRequest, pk=pk)
    
    if stock_request.status != StockRequest.PENDING:
        messages.error(request, "This request has already been processed.")
        return redirect('inventory:stock_request_detail', pk=pk)
    
    # Check if product has enough stock
    product = stock_request.product
    if stock_request.quantity > product.quantity:
        messages.error(request, f"Insufficient stock. Available: {product.quantity}, Requested: {stock_request.quantity}")
        return redirect('inventory:stock_request_detail', pk=pk)
    
    if request.method == 'POST':
        # Update stock request
        stock_request.status = StockRequest.APPROVED
        stock_request.approved_by = request.user
        stock_request.save()
        
        # Update product quantity
        old_quantity = product.quantity
        product.quantity -= stock_request.quantity
        product.save()
        
        # Create inventory log
        InventoryLog.objects.create(
            product=product,
            user=request.user,
            quantity_change=-stock_request.quantity,
            previous_quantity=old_quantity,
            new_quantity=product.quantity,
            action=InventoryLog.REDUCTION,
            note=f'Stock request #{stock_request.id} approved'
        )
        
        # Create notification for the employee
        Notification.create_notification(
            user=stock_request.employee,
            title="Stock Request Approved",
            message=f"Your request for {stock_request.quantity} units of {product.name} has been approved.",
            notification_type=Notification.INVENTORY
        )
        
        messages.success(request, f"Stock request for {product.name} has been approved.")
        return redirect('inventory:stock_request_list')
    
    return render(request, 'inventory/approve_stock_request.html', {'request': stock_request})

@login_required
def reject_stock_request(request, pk):
    """Reject a stock request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to reject stock requests.")
        return redirect('inventory:index')
    
    stock_request = get_object_or_404(StockRequest, pk=pk)
    
    if stock_request.status != StockRequest.PENDING:
        messages.error(request, "This request has already been processed.")
        return redirect('inventory:stock_request_detail', pk=pk)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        # Update stock request
        stock_request.status = StockRequest.REJECTED
        stock_request.approved_by = request.user
        stock_request.rejection_reason = rejection_reason
        stock_request.save()
        
        # Create notification for the employee
        Notification.create_notification(
            user=stock_request.employee,
            title="Stock Request Rejected",
            message=f"Your request for {stock_request.quantity} units of {stock_request.product.name} has been rejected.",
            notification_type=Notification.INVENTORY
        )
        
        messages.success(request, f"Stock request has been rejected.")
        return redirect('inventory:stock_request_list')
    
    return render(request, 'inventory/reject_stock_request.html', {'request': stock_request})

# Employee Views
@login_required
def view_stock(request):
    """View available stock (for employees)"""
    products = Product.objects.select_related('category', 'supplier').all()
    
    # Apply filters
    product_filter = ProductFilter(request.GET, queryset=products)
    products = product_filter.qs
    
    # Paginate the results
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/view_stock.html', {
        'page_obj': page_obj,
        'product_filter': product_filter,
    })

# Analytics and Reporting
@login_required
def inventory_analytics(request):
    """Inventory analytics dashboard"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to view analytics.")
        return redirect('inventory:index')
    
    # Total products and value
    total_products = Product.objects.count()
    total_value = Product.objects.aggregate(
        value=Sum(F('price') * F('quantity'))
    )['value'] or 0
    
    # Category breakdown
    categories = Category.objects.annotate(
        products_count=Count('products'),
        total_value=Sum(F('products__price') * F('products__quantity'))
    ).order_by('-total_value')
    
    # Low stock products
    low_stock = Product.objects.filter(
        quantity__lt=F('threshold_quantity')
    ).select_related('category', 'supplier')
    
    # Top products by value
    top_products = Product.objects.annotate(
        value=F('price') * F('quantity')
    ).order_by('-value')[:10]
    
    # Monthly stock changes (last 6 months)
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_logs = InventoryLog.objects.filter(
        created_at__gte=six_months_ago
    ).extra(
        select={'month': "to_char(created_at, 'YYYY-MM')"}
    ).values('month', 'action').annotate(
        count=Count('id'),
        total_change=Sum('quantity_change')
    ).order_by('month')
    
    # Process logs for chart
    months = []
    additions = []
    reductions = []
    
    # Create a dictionary for easy access
    log_dict = {}
    for log in monthly_logs:
        month = log['month']
        action = log['action']
        change = log['total_change']
        
        if month not in log_dict:
            log_dict[month] = {'addition': 0, 'reduction': 0, 'adjustment': 0}
        
        log_dict[month][action] = change
    
    # Sort by month
    for month in sorted(log_dict.keys()):
        months.append(month)
        additions.append(log_dict[month]['addition'])
        reductions.append(abs(log_dict[month]['reduction']))
    
    context = {
        'total_products': total_products,
        'total_value': total_value,
        'categories': categories,
        'low_stock': low_stock,
        'top_products': top_products,
        'chart_data': {
            'months': months,
            'additions': additions,
            'reductions': reductions,
        }
    }
    
    return render(request, 'inventory/analytics.html', context)

@login_required
def export_inventory(request):
    """Export inventory data page"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to export inventory data.")
        return redirect('inventory:index')
    
    return render(request, 'inventory/export.html')

@login_required
def export_inventory_pdf(request):
    """Export inventory data as PDF"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to export inventory data.")
        return redirect('inventory:index')
    
    # Get filter parameters
    category_id = request.GET.get('category', None)
    low_stock_only = request.GET.get('low_stock', False) == 'true'
    
    # Filter products
    products = Product.objects.select_related('category', 'supplier')
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if low_stock_only:
        products = products.filter(quantity__lt=F('threshold_quantity'))
    
    # Generate PDF
    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    pdf = generate_inventory_pdf(products)
    response.write(pdf)
    
    return response

@login_required
def export_inventory_excel(request):
    """Export inventory data as Excel"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to export inventory data.")
        return redirect('inventory:index')
    
    # Get filter parameters
    category_id = request.GET.get('category', None)
    low_stock_only = request.GET.get('low_stock', False) == 'true'
    
    # Filter products
    products = Product.objects.select_related('category', 'supplier')
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if low_stock_only:
        products = products.filter(quantity__lt=F('threshold_quantity'))
    
    # Generate Excel file
    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    excel_file = generate_inventory_excel(products)
    
    response = HttpResponse(
        excel_file,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

# API Endpoints for HTMX
@login_required
def product_search(request):
    """Search products for HTMX requests"""
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(sku__icontains=query) |
        Q(category__name__icontains=query)
    ).select_related('category')[:10]
    
    context = {'products': products, 'query': query}
    
    if request.headers.get('HX-Request'):
        return render(request, 'inventory/partials/product_search_results.html', context)
    return JsonResponse({'results': list(products.values('id', 'name', 'sku', 'price', 'quantity'))})

@login_required
def low_stock_products(request):
    """Get low stock products for HTMX requests"""
    products = Product.objects.filter(
        quantity__lt=F('threshold_quantity')
    ).select_related('category', 'supplier')
    
    if request.headers.get('HX-Request'):
        return render(request, 'inventory/partials/low_stock_table.html', {'products': products})
    return JsonResponse({'count': products.count()})
