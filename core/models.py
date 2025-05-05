from django.db import models
from django.conf import settings

class Notification(models.Model):
    """Model for system notifications"""
    INVENTORY = 'inventory'
    ATTENDANCE = 'attendance'
    MESSENGER = 'messenger'
    SYSTEM = 'system'
    
    TYPE_CHOICES = (
        (INVENTORY, 'Inventory'),
        (ATTENDANCE, 'Attendance'),
        (MESSENGER, 'Messenger'),
        (SYSTEM, 'System'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=SYSTEM)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    @classmethod
    def create_notification(cls, user, title, message, notification_type=SYSTEM, link=None):
        """Helper method to create a notification"""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
