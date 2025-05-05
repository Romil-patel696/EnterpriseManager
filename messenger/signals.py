from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message

@receiver(post_save, sender=Message)
def message_notification(sender, instance, created, **kwargs):
    """Send notification when a new message is created"""
    if created:
        # This is where you would implement real-time notifications
        # via WebSockets or other mechanisms
        pass