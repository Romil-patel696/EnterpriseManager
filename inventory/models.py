from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.urls import reverse

class Category(models.Model):
    """Product category model"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Supplier(models.Model):
    """Supplier model"""
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Product model"""
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=0)
    threshold_quantity = models.PositiveIntegerField(default=10, help_text="Minimum stock level before alert")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def get_absolute_url(self):
        return reverse('inventory:product_detail', args=[str(self.id)])
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.threshold_quantity

class StockRequest(models.Model):
    """Stock request model for employees"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_requests')
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stock_requests')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_stock_requests'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} units - {self.get_status_display()}"

class InventoryLog(models.Model):
    """Log for inventory changes"""
    ADDITION = 'addition'
    REDUCTION = 'reduction'
    ADJUSTMENT = 'adjustment'
    
    ACTION_CHOICES = (
        (ADDITION, 'Addition'),
        (REDUCTION, 'Reduction'),
        (ADJUSTMENT, 'Adjustment'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inventory_logs')
    quantity_change = models.IntegerField()
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.action} - {self.quantity_change} units"
