from django.contrib import admin
from .models import Attendance, Leave, LeaveType, Policy

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    list_filter = ('date', 'status')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name')
    date_hierarchy = 'date'

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'days_allowed')

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'duration')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name', 'reason')
    date_hierarchy = 'start_date'
    
    def duration(self, obj):
        days = obj.get_duration()
        return f"{days} {'day' if days == 1 else 'days'}"
    duration.short_description = 'Duration'

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'description')
