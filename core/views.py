from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification
from inventory.models import Product, StockRequest
from attendance.models import Attendance, Leave
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from django.contrib import messages
from django.db import models

def index(request):
    """Landing page view"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/index.html')

@login_required
def dashboard(request):
    """Dashboard view based on user role"""
    user = request.user
    context = {}
    
    if user.is_employer:
        # Get employer statistics
        today = timezone.now().date()
        employees_count = user.__class__.objects.filter(
            userprofile__role='employee'
        ).count()
        
        active_today = Attendance.objects.filter(
            date=today,
            status=Attendance.APPROVED
        ).count()
        
        pending_leave_requests = Leave.objects.filter(
            status=Leave.PENDING
        ).count()
        
        low_stock_products = Product.objects.filter(
            quantity__lt=models.F('threshold_quantity')
        ).count()
        
        # Get attendance statistics
        attendance_stats = Attendance.objects.filter(
            date__gte=today - timezone.timedelta(days=30)
        ).values('date').annotate(
            count=Count('id'),
            approved=Count('id', filter=Q(status=Attendance.APPROVED)),
            rejected=Count('id', filter=Q(status=Attendance.REJECTED)),
            pending=Count('id', filter=Q(status=Attendance.PENDING))
        ).order_by('date')
        
        # Get inventory statistics
        product_categories = Product.objects.values('category').annotate(
            count=Count('id'),
            total_value=Sum(models.F('price') * models.F('quantity'))
        ).order_by('-total_value')
        
        context = {
            'is_employer': True,
            'employees_count': employees_count,
            'active_today': active_today,
            'pending_leave_requests': pending_leave_requests,
            'low_stock_products': low_stock_products,
            'attendance_stats': list(attendance_stats),
            'product_categories': list(product_categories)
        }
        
        return render(request, 'core/employer_dashboard.html', context)
    else:
        # Get employee statistics
        today = timezone.now().date()
        attendance_today = Attendance.objects.filter(
            employee=user,
            date=today
        ).first()
        
        pending_stock_requests = StockRequest.objects.filter(
            employee=user,
            status=StockRequest.PENDING
        ).count()
        
        leave_balance = getattr(user.userprofile, 'leave_balance', {'casual': 0, 'sick': 0})
        
        # Get attendance history
        attendance_history = Attendance.objects.filter(
            employee=user,
            date__gte=today - timezone.timedelta(days=30)
        ).order_by('-date')
        
        context = {
            'is_employee': True,
            'attendance_today': attendance_today,
            'pending_stock_requests': pending_stock_requests,
            'leave_balance': leave_balance,
            'attendance_history': attendance_history
        }
        
        return render(request, 'core/employee_dashboard.html', context)

@login_required
def notifications_list(request):
    """View for listing all notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/notifications.html', {
        'notifications': notifications
    })

@login_required
def mark_notification_as_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    # If it's not an AJAX request, redirect back to the notifications page
    messages.success(request, 'Notification marked as read.')
    return redirect('core:notifications')

@login_required
def mark_all_notifications_as_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    # If it's not an AJAX request, redirect back to the notifications page
    messages.success(request, 'All notifications marked as read.')
    return redirect('core:notifications')

def handle_404(request, exception):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)

def handle_500(request):
    """Custom 500 error handler"""
    return render(request, '500.html', status=500)
