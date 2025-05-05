from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile, User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for every new User"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    """Save UserProfile when User is saved"""
    # Only try to save the userprofile if it's not a new user
    # and if the userprofile exists to prevent errors
    if not created:
        try:
            instance.userprofile.save()
        except UserProfile.DoesNotExist:
            # Create a profile if it doesn't exist
            UserProfile.objects.create(user=instance)