from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import StockRequest, Product

@receiver(post_save, sender=StockRequest)
def update_product_stock(sender, instance, created, **kwargs):
    """Update product stock levels when a stock request is approved"""
    if instance.status == StockRequest.APPROVED and instance.is_processed is False:
        product = instance.product
        
        if instance.request_type == StockRequest.ADDITION:
            product.current_stock += instance.quantity
        elif instance.request_type == StockRequest.DEDUCTION:
            product.current_stock -= instance.quantity
        
        product.save()
        
        # Mark the request as processed
        instance.is_processed = True
        instance.save(update_fields=['is_processed'])

@receiver(pre_save, sender=Product)
def check_low_stock(sender, instance, **kwargs):
    """Check if product has reached low stock threshold"""
    if instance.pk:  # Only for existing products
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            if (old_instance.current_stock > instance.low_stock_threshold and 
                instance.current_stock <= instance.low_stock_threshold):
                # Product has reached low stock threshold
                # Logic for notifications would go here
                pass
        except Product.DoesNotExist:
            pass