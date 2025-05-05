from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta

class LeaveType(models.Model):
    """Model for different types of leaves (e.g. Casual Leave, Sick Leave)"""
    name = models.CharField(max_length=50)
    days_allowed = models.PositiveIntegerField(help_text="Number of days allowed per year")
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    """Model to track leave balance for each employee"""
    employee = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_balance')
    casual_leave = models.FloatField(default=0)
    sick_leave = models.FloatField(default=0)
    year = models.PositiveIntegerField(default=timezone.now().year)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.employee.username}'s leave balance"
    
    def get_balance_for_type(self, leave_type_name):
        """Return leave balance based on leave type name"""
        if leave_type_name.lower() == 'casual leave':
            return self.casual_leave
        elif leave_type_name.lower() == 'sick leave':
            return self.sick_leave
        return 0
    
    def update_balance(self, leave_type_name, days_used):
        """Update leave balance based on leave type and days used"""
        if leave_type_name.lower() == 'casual leave':
            self.casual_leave -= days_used
            if self.casual_leave < 0:
                self.casual_leave = 0
        elif leave_type_name.lower() == 'sick leave':
            self.sick_leave -= days_used
            if self.sick_leave < 0:
                self.sick_leave = 0
        self.save()

class Leave(models.Model):
    """Model for leave requests"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (CANCELLED, 'Cancelled'),
    )
    
    FULL_DAY = 'full'
    HALF_DAY = 'half'
    
    DAY_TYPE_CHOICES = (
        (FULL_DAY, 'Full Day'),
        (HALF_DAY, 'Half Day'),
    )
    
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='leaves')
    start_date = models.DateField()
    end_date = models.DateField()
    day_type = models.CharField(max_length=4, choices=DAY_TYPE_CHOICES, default=FULL_DAY)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_leaves'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_processed = models.BooleanField(default=False, help_text="Flag to track if leave balance has been updated")
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee.username} - {self.leave_type.name} - {self.start_date}"
    
    def clean(self):
        # End date should not be before start date
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date")
        
        # Check for overlapping leave requests
        overlapping_leaves = Leave.objects.filter(
            employee=self.employee,
            status__in=[self.APPROVED, self.PENDING],
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        
        if self.pk:
            overlapping_leaves = overlapping_leaves.exclude(pk=self.pk)
        
        if overlapping_leaves.exists():
            raise ValidationError("You already have a leave request for this period")
    
    def get_duration(self):
        """Calculate the duration of leave in days"""
        delta = self.end_date - self.start_date
        days = delta.days + 1  # Include both start and end date
        
        if self.day_type == self.HALF_DAY:
            days = days * 0.5
        
        return days
    
    def get_business_days(self):
        """Calculate the number of business days (excluding weekends)"""
        days = 0
        current_date = self.start_date
        
        while current_date <= self.end_date:
            # Skip weekends (5=Saturday, 6=Sunday)
            if current_date.weekday() < 5:
                days += 1
            current_date += timedelta(days=1)
        
        if self.day_type == self.HALF_DAY:
            days = days * 0.5
            
        return days

class Attendance(models.Model):
    """Model for employee attendance"""
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    )
    
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.now)
    check_in = models.TimeField()
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_attendances'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_processed = models.BooleanField(default=False, help_text="Flag to track if attendance has been processed")
    
    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', '-check_in']
    
    def __str__(self):
        return f"{self.employee.username} - {self.date}"
    
    def get_duration(self):
        """Calculate the duration of attendance in hours"""
        if not self.check_out:
            return None
        
        check_in_dt = datetime.combine(self.date, self.check_in)
        check_out_dt = datetime.combine(self.date, self.check_out)
        
        # Handle case where check-out is on the next day
        if check_out_dt < check_in_dt:
            check_out_dt += timedelta(days=1)
        
        delta = check_out_dt - check_in_dt
        return delta.total_seconds() / 3600  # Convert to hours
    
    def is_late(self):
        """Check if employee checked in late based on policy"""
        try:
            start_time = Policy.objects.get(name='work_day_start').time_value
            if self.check_in > start_time:
                return True
        except Policy.DoesNotExist:
            # Default to 9:00 AM if policy not set
            default_time = datetime.strptime('09:00', '%H:%M').time()
            if self.check_in > default_time:
                return True
        return False

class Policy(models.Model):
    """Model for attendance policies"""
    TIME = 'time'
    INTEGER = 'integer'
    FLOAT = 'float'
    BOOLEAN = 'boolean'
    
    DATA_TYPE_CHOICES = (
        (TIME, 'Time'),
        (INTEGER, 'Integer'),
        (FLOAT, 'Float'),
        (BOOLEAN, 'Boolean'),
    )
    
    name = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=50)
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES)
    description = models.TextField()
    
    class Meta:
        verbose_name_plural = "Policies"
    
    def __str__(self):
        return f"{self.name}: {self.value}"
    
    @property
    def time_value(self):
        """Return time value if data_type is time"""
        if self.data_type == self.TIME:
            try:
                return datetime.strptime(self.value, '%H:%M').time()
            except ValueError:
                return None
        return None
    
    @property
    def int_value(self):
        """Return integer value if data_type is integer"""
        if self.data_type == self.INTEGER:
            try:
                return int(self.value)
            except ValueError:
                return 0
        return 0
    
    @property
    def float_value(self):
        """Return float value if data_type is float"""
        if self.data_type == self.FLOAT:
            try:
                return float(self.value)
            except ValueError:
                return 0.0
        return 0.0
    
    @property
    def bool_value(self):
        """Return boolean value if data_type is boolean"""
        if self.data_type == self.BOOLEAN:
            return self.value.lower() in ('true', 'yes', '1')
        return False
