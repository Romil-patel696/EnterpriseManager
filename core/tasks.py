from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_email_notification(subject, message, recipient_list):
    """Send email notification as a background task"""
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )
    return f"Email sent to {', '.join(recipient_list)}"

@shared_task
def create_system_notification(user_id, title, message, notification_type, link=None):
    """Create system notification as a background task"""
    try:
        user = User.objects.get(id=user_id)
        Notification.create_notification(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
        return f"Notification created for user {user.username}"
    except User.DoesNotExist:
        return f"Failed to create notification: User with ID {user_id} not found"

@shared_task
def send_low_stock_alerts():
    """Check for low stock and send alerts"""
    from inventory.models import Product
    from django.db.models import F
    
    # Get products with quantity below threshold
    low_stock_products = Product.objects.filter(quantity__lt=F('threshold_quantity'))
    
    if low_stock_products.exists():
        # Get all employers
        employers = User.objects.filter(userprofile__role='employer')
        
        for product in low_stock_products:
            # Create notification for each employer
            for employer in employers:
                Notification.create_notification(
                    user=employer,
                    title=f"Low Stock Alert: {product.name}",
                    message=f"The stock level for {product.name} is below the threshold. Current stock: {product.quantity}, Threshold: {product.threshold_quantity}",
                    notification_type=Notification.INVENTORY,
                    link=f"/inventory/products/{product.id}/"
                )
        
        # Send email to the first employer (or adjust as needed)
        if employers.exists():
            product_list = "\n".join([f"- {p.name}: {p.quantity}/{p.threshold_quantity}" for p in low_stock_products])
            send_email_notification.delay(
                subject="Low Stock Alert",
                message=f"The following products are below their threshold levels:\n\n{product_list}",
                recipient_list=[employers.first().email]
            )
    
    return f"Checked {low_stock_products.count()} low stock products"
