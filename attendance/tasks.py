from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, time, timedelta
from .models import Attendance, Leave, LeaveBalance, Policy
from .utils import mark_absent_employees
from core.models import Notification
from accounts.models import UserProfile

User = get_user_model()

@shared_task
def auto_mark_absent():
    """
    Automatically mark employees as absent if they haven't checked in
    This task should be scheduled to run at the end of each working day
    """
    mark_absent_employees()
    return "Marked absent employees"

@shared_task
def send_attendance_reminders():
    """
    Send reminders to employees who haven't checked in yet
    This task should be scheduled to run mid-morning
    """
    today = timezone.now().date()
    current_time = timezone.now().time()
    
    # Only send reminders during work hours (9 AM to 5 PM)
    if not (time(9, 0) <= current_time <= time(17, 0)):
        return "Not during work hours, skipping reminders"
    
    # Get all employees
    employees = User.objects.filter(userprofile__role=UserProfile.EMPLOYEE)
    
    # Find employees who haven't checked in today
    reminded_count = 0
    for employee in employees:
        if not Attendance.objects.filter(employee=employee, date=today).exists():
            # Create notification for the employee
            Notification.create_notification(
                user=employee,
                title="Attendance Reminder",
                message="You haven't checked in today. Please check in if you are working.",
                notification_type=Notification.ATTENDANCE,
                link="/attendance/request/"
            )
            reminded_count += 1
    
    return f"Sent attendance reminders to {reminded_count} employees"

@shared_task
def process_leave_notifications():
    """
    Send notifications for upcoming and approved leaves
    This task should be scheduled to run daily
    """
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    # Find leaves starting tomorrow
    upcoming_leaves = Leave.objects.filter(
        status=Leave.APPROVED,
        start_date=tomorrow
    ).select_related('employee', 'leave_type')
    
    # Notify employees about their leave starting tomorrow
    for leave in upcoming_leaves:
        Notification.create_notification(
            user=leave.employee,
            title="Leave Reminder",
            message=f"Your {leave.leave_type.name} leave starts tomorrow.",
            notification_type=Notification.ATTENDANCE
        )
    
    # Find leaves ending today
    ending_leaves = Leave.objects.filter(
        status=Leave.APPROVED,
        end_date=today
    ).select_related('employee', 'leave_type')
    
    # Notify employees about their leave ending today
    for leave in ending_leaves:
        Notification.create_notification(
            user=leave.employee,
            title="Leave Ending",
            message=f"Your {leave.leave_type.name} leave ends today. Remember to check in tomorrow.",
            notification_type=Notification.ATTENDANCE
        )
    
    return f"Processed notifications for {upcoming_leaves.count()} upcoming and {ending_leaves.count()} ending leaves"

@shared_task
def reset_yearly_leave_balances():
    """
    Reset leave balances at the beginning of a new year
    This task should be scheduled to run on January 1st
    """
    current_year = timezone.now().year
    
    # Get default leave values from policy
    try:
        casual_leave_default = int(Policy.objects.get(name='default_casual_leaves').value)
    except (Policy.DoesNotExist, ValueError):
        casual_leave_default = 12
    
    try:
        sick_leave_default = int(Policy.objects.get(name='default_sick_leaves').value)
    except (Policy.DoesNotExist, ValueError):
        sick_leave_default = 10
    
    # Get all employees
    employees = User.objects.filter(userprofile__role=UserProfile.EMPLOYEE)
    
    # Create new leave balances for the new year
    created_count = 0
    for employee in employees:
        LeaveBalance.objects.create(
            employee=employee,
            year=current_year,
            casual_leave=casual_leave_default,
            sick_leave=sick_leave_default
        )
        created_count += 1
        
        # Notify employee about new leave balance
        Notification.create_notification(
            user=employee,
            title="New Leave Balance",
            message=f"Your leave balance has been reset for the new year. You have {casual_leave_default} casual leaves and {sick_leave_default} sick leaves.",
            notification_type=Notification.ATTENDANCE
        )
    
    return f"Reset leave balances for {created_count} employees for year {current_year}"
