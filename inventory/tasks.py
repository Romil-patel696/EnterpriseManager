from celery import shared_task
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Product
from accounts.models import UserProfile
from core.models import Notification

User = get_user_model()

@shared_task
def check_low_stock_levels():
    """
    Task to check for products with stock below threshold and send notifications
    """
    # Find products with low stock
    low_stock_products = Product.objects.filter(quantity__lt=F('threshold_quantity'))
    
    if low_stock_products.exists():
        # Get all employers (admins)
        employers = User.objects.filter(userprofile__role=UserProfile.EMPLOYER)
        
        # Generate notification text
        product_list = "\n".join([
            f"- {product.name} (SKU: {product.sku}): {product.quantity} remaining (threshold: {product.threshold_quantity})"
            for product in low_stock_products
        ])
        
        email_subject = f"Low Stock Alert - {low_stock_products.count()} products below threshold"
        email_message = f"""
        The following products are currently below their stock threshold levels:
        
        {product_list}
        
        Please review and restock as necessary.
        """
        
        # Create in-app notification for each employer
        for employer in employers:
            Notification.create_notification(
                user=employer,
                title=f"Low Stock Alert: {low_stock_products.count()} products",
                message=f"{low_stock_products.count()} products are below their threshold levels.",
                notification_type=Notification.INVENTORY,
                link="/inventory/analytics/"
            )
        
        # Send email to all employers
        employer_emails = employers.values_list('email', flat=True)
        if employer_emails:
            send_mail(
                subject=email_subject,
                message=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(employer_emails),
                fail_silently=False,
            )
        
        return f"Sent low stock notifications for {low_stock_products.count()} products"
    
    return "No low stock products found"

@shared_task
def notify_stock_request_status(request_id, status):
    """
    Task to notify employees about stock request status changes
    """
    from .models import StockRequest
    
    try:
        stock_request = StockRequest.objects.select_related('product', 'employee').get(id=request_id)
        
        status_text = dict(StockRequest.STATUS_CHOICES).get(status, "updated")
        
        # Create notification for the employee
        Notification.create_notification(
            user=stock_request.employee,
            title=f"Stock Request {status_text.title()}",
            message=f"Your request for {stock_request.quantity} units of {stock_request.product.name} has been {status_text}.",
            notification_type=Notification.INVENTORY,
            link=f"/inventory/requests/{stock_request.id}/"
        )
        
        return f"Sent notification for stock request #{request_id}"
    
    except StockRequest.DoesNotExist:
        return f"Stock request #{request_id} not found"
