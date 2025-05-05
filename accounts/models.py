from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Extended User model"""
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return self.username
    
    @property
    def is_employer(self):
        try:
            return self.userprofile.role == UserProfile.EMPLOYER
        except UserProfile.DoesNotExist:
            return False
    
    @property
    def is_employee(self):
        try:
            return self.userprofile.role == UserProfile.EMPLOYEE
        except UserProfile.DoesNotExist:
            return False

class UserProfile(models.Model):
    """User profile model with additional information"""
    EMPLOYER = 'employer'
    EMPLOYEE = 'employee'
    
    ROLE_CHOICES = (
        (EMPLOYER, 'Employer (Admin)'),
        (EMPLOYEE, 'Employee (User)'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=EMPLOYEE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=50, blank=True, null=True)
    position = models.CharField(max_length=50, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    employer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

# Signal handlers are defined in signals.py
