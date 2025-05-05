from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Attendance, Leave, LeaveBalance

@receiver(post_save, sender=Leave)
def update_leave_balance(sender, instance, created, **kwargs):
    """Update leave balance when a leave request is approved"""
    if instance.status == Leave.APPROVED and not instance.is_processed:
        # Get or create leave balance for the employee
        leave_balance, _ = LeaveBalance.objects.get_or_create(
            employee=instance.employee,
            year=instance.start_date.year
        )
        
        # Update balance based on leave type and duration
        leave_type_name = instance.leave_type.name.lower()
        duration = instance.get_business_days()
        leave_balance.update_balance(leave_type_name, duration)
        
        # Mark as processed to avoid double-counting
        instance.is_processed = True
        instance.save(update_fields=['is_processed'])

@receiver(post_save, sender=Attendance)
def process_attendance_status(sender, instance, created, **kwargs):
    """Process attendance status changes"""
    if created or instance.status == Attendance.APPROVED:
        # This is where you would implement attendance-related
        # processing, such as notifying managers about late arrivals
        # or updating attendance statistics
        pass