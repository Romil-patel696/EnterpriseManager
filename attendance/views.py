from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from datetime import datetime, timedelta, time
from .models import Attendance, Leave, LeaveType, LeaveBalance, Policy
from .forms import AttendanceRequestForm, LeaveRequestForm, PolicyForm
from .utils import generate_attendance_report_pdf, generate_attendance_report_excel
from core.models import Notification
from accounts.models import User, UserProfile
import csv

# Helper function to check policies
def get_policy_value(name, default=None):
    try:
        policy = Policy.objects.get(name=name)
        if policy.data_type == 'time':
            return policy.time_value
        elif policy.data_type == 'integer':
            return policy.int_value
        elif policy.data_type == 'float':
            return policy.float_value
        elif policy.data_type == 'boolean':
            return policy.bool_value
        return policy.value
    except Policy.DoesNotExist:
        return default

@login_required
def index(request):
    """Attendance module index page"""
    user = request.user
    context = {}
    
    # Get current date info
    today = timezone.now().date()
    
    if user.is_employer:
        # Employer dashboard
        today_attendance = Attendance.objects.filter(date=today)
        total_employees = User.objects.filter(userprofile__role=UserProfile.EMPLOYEE).count()
        
        # Today's stats
        present_count = today_attendance.filter(status=Attendance.APPROVED).count()
        pending_count = today_attendance.filter(status=Attendance.PENDING).count()
        absent_count = total_employees - present_count - pending_count
        
        # Pending approvals
        pending_attendance = Attendance.objects.filter(status=Attendance.PENDING).select_related('employee')
        pending_leaves = Leave.objects.filter(status=Leave.PENDING).select_related('employee', 'leave_type')
        
        # Recent activity
        recent_activity = list(Attendance.objects.filter(
            status=Attendance.APPROVED
        ).select_related('employee').order_by('-created_at')[:10])
        
        context.update({
            'is_employer': True,
            'today': today,
            'present_count': present_count,
            'pending_count': pending_count,
            'absent_count': absent_count,
            'total_employees': total_employees,
            'pending_attendance': pending_attendance[:5],
            'pending_leaves': pending_leaves[:5],
            'pending_attendance_count': pending_attendance.count(),
            'pending_leaves_count': pending_leaves.count(),
            'recent_activity': recent_activity,
        })
    else:
        # Employee dashboard
        # Check today's attendance
        try:
            today_attendance = Attendance.objects.get(employee=user, date=today)
            checked_in = True
            attendance_status = today_attendance.status
            check_in_time = today_attendance.check_in
            check_out_time = today_attendance.check_out
        except Attendance.DoesNotExist:
            checked_in = False
            attendance_status = None
            check_in_time = None
            check_out_time = None
        
        # Recent attendance history
        attendance_history = Attendance.objects.filter(
            employee=user
        ).order_by('-date')[:5]
        
        # Leave balance
        try:
            leave_balance = LeaveBalance.objects.get(employee=user)
        except LeaveBalance.DoesNotExist:
            leave_balance = None
        
        # Pending leave requests
        pending_leaves = Leave.objects.filter(
            employee=user, 
            status=Leave.PENDING
        ).select_related('leave_type')
        
        context.update({
            'is_employee': True,
            'today': today,
            'checked_in': checked_in,
            'attendance_status': attendance_status,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'attendance_history': attendance_history,
            'leave_balance': leave_balance,
            'pending_leaves': pending_leaves,
        })
    
    return render(request, 'attendance/index.html', context)

@login_required
def attendance_request(request):
    """Handle attendance check-in and check-out requests"""
    today = timezone.now().date()
    
    try:
        # Check if already checked in today
        attendance = Attendance.objects.get(employee=request.user, date=today)
        checked_in = True
        
        # If already checked out, show message
        if attendance.check_out:
            messages.info(request, "You have already checked out for today.")
            return redirect('attendance:index')
            
    except Attendance.DoesNotExist:
        attendance = None
        checked_in = False
    
    if request.method == 'POST':
        form = AttendanceRequestForm(request.POST, instance=attendance)
        
        if form.is_valid():
            attendance_obj = form.save(commit=False)
            
            if not checked_in:
                # New check-in
                attendance_obj.employee = request.user
                attendance_obj.date = today
                attendance_obj.check_in = timezone.now().time()
                messages.success(request, "Check-in recorded successfully. Awaiting approval.")
            else:
                # Check-out
                attendance_obj.check_out = timezone.now().time()
                messages.success(request, "Check-out recorded successfully.")
            
            attendance_obj.save()
            
            # Notify employers about new attendance
            employers = User.objects.filter(userprofile__role=UserProfile.EMPLOYER)
            for employer in employers:
                action = "checked in" if not checked_in else "checked out"
                Notification.create_notification(
                    user=employer,
                    title=f"Attendance: {request.user.get_full_name() or request.user.username} {action}",
                    message=f"{request.user.get_full_name() or request.user.username} has {action} at {timezone.now().strftime('%H:%M')}.",
                    notification_type=Notification.ATTENDANCE,
                    link=f"/attendance/admin/approvals/{attendance_obj.id}/"
                )
            
            return redirect('attendance:index')
    else:
        form = AttendanceRequestForm(instance=attendance)
    
    work_start = get_policy_value('work_day_start', time(9, 0))
    work_end = get_policy_value('work_day_end', time(17, 0))
    
    context = {
        'form': form,
        'checked_in': checked_in,
        'attendance': attendance,
        'today': today,
        'current_time': timezone.now().time(),
        'work_start': work_start,
        'work_end': work_end,
    }
    
    return render(request, 'attendance/attendance_request.html', context)

@login_required
def attendance_history(request):
    """View attendance history for the employee"""
    # Get date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('status')
    
    # Default to last 30 days if no date range specified
    if not start_date:
        start_date = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().date().strftime('%Y-%m-%d')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format. Using default date range.")
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
    
    # Query attendance records
    attendance_query = Attendance.objects.filter(
        employee=request.user,
        date__range=[start_date, end_date]
    )
    
    if status_filter:
        attendance_query = attendance_query.filter(status=status_filter)
    
    attendance_records = attendance_query.order_by('-date')
    
    # Statistics
    total_days = (end_date - start_date).days + 1
    present_days = attendance_records.filter(status=Attendance.APPROVED).count()
    pending_days = attendance_records.filter(status=Attendance.PENDING).count()
    absent_days = total_days - present_days - pending_days
    
    # Calculate work hours
    total_hours = 0
    for record in attendance_records.filter(status=Attendance.APPROVED, check_out__isnull=False):
        duration = record.get_duration()
        if duration:
            total_hours += duration
    
    # Paginate results
    paginator = Paginator(attendance_records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_days': total_days,
        'present_days': present_days,
        'pending_days': pending_days,
        'absent_days': absent_days,
        'total_hours': total_hours,
        'start_date': start_date,
        'end_date': end_date,
        'status_filter': status_filter,
    }
    
    return render(request, 'attendance/attendance_log.html', context)

@login_required
def leave_request(request):
    """Handle leave request submissions"""
    # Get available leave types
    leave_types = LeaveType.objects.all()
    
    # Get leave balance
    try:
        leave_balance = LeaveBalance.objects.get(employee=request.user)
    except LeaveBalance.DoesNotExist:
        leave_balance = LeaveBalance.objects.create(
            employee=request.user,
            casual_leave=get_policy_value('default_casual_leaves', 12),
            sick_leave=get_policy_value('default_sick_leaves', 10)
        )
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = request.user
            
            # Check leave balance
            leave_type = leave.leave_type
            duration = leave.get_business_days()
            
            if leave_type.name.lower() == 'casual leave':
                balance = leave_balance.casual_leave
            elif leave_type.name.lower() == 'sick leave':
                balance = leave_balance.sick_leave
            else:
                balance = 0
            
            if duration > balance:
                messages.error(request, f"Insufficient leave balance. You have {balance} days of {leave_type.name} left.")
                return render(request, 'attendance/leave_request.html', {
                    'form': form,
                    'leave_types': leave_types,
                    'leave_balance': leave_balance
                })
            
            try:
                leave.clean()  # Run model validation
                leave.save()
                
                # Notify employers about new leave request
                employers = User.objects.filter(userprofile__role=UserProfile.EMPLOYER)
                for employer in employers:
                    Notification.create_notification(
                        user=employer,
                        title=f"New Leave Request: {request.user.get_full_name() or request.user.username}",
                        message=f"{request.user.get_full_name() or request.user.username} has requested {duration} day(s) of {leave_type.name} from {leave.start_date} to {leave.end_date}.",
                        notification_type=Notification.ATTENDANCE,
                        link=f"/attendance/admin/leave-approvals/{leave.id}/"
                    )
                
                messages.success(request, "Leave request submitted successfully. Waiting for approval.")
                return redirect('attendance:leave_history')
                
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LeaveRequestForm()
    
    context = {
        'form': form,
        'leave_types': leave_types,
        'leave_balance': leave_balance
    }
    
    return render(request, 'attendance/leave_request.html', context)

@login_required
def leave_history(request):
    """View leave history for the employee"""
    # Get filter
    status_filter = request.GET.get('status')
    year_filter = request.GET.get('year', timezone.now().year)
    
    try:
        year_filter = int(year_filter)
    except ValueError:
        year_filter = timezone.now().year
    
    # Query leave records
    leave_query = Leave.objects.filter(employee=request.user)
    
    if status_filter:
        leave_query = leave_query.filter(status=status_filter)
    
    if year_filter:
        leave_query = leave_query.filter(
            Q(start_date__year=year_filter) | Q(end_date__year=year_filter)
        )
    
    leave_records = leave_query.select_related('leave_type').order_by('-start_date')
    
    # Get leave balance
    try:
        leave_balance = LeaveBalance.objects.get(employee=request.user)
    except LeaveBalance.DoesNotExist:
        leave_balance = None
    
    # Statistics
    approved_leaves = leave_records.filter(status=Leave.APPROVED)
    casual_days_taken = sum([leave.get_business_days() for leave in approved_leaves.filter(leave_type__name__icontains='casual')])
    sick_days_taken = sum([leave.get_business_days() for leave in approved_leaves.filter(leave_type__name__icontains='sick')])
    
    # Paginate results
    paginator = Paginator(leave_records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Available years for filter (start from current year and go back 5 years)
    available_years = list(range(timezone.now().year, timezone.now().year - 6, -1))
    
    context = {
        'page_obj': page_obj,
        'leave_balance': leave_balance,
        'casual_days_taken': casual_days_taken,
        'sick_days_taken': sick_days_taken,
        'status_filter': status_filter,
        'year_filter': year_filter,
        'available_years': available_years,
    }
    
    return render(request, 'attendance/leave_balance.html', context)

@login_required
def leave_detail(request, pk):
    """View details of a leave request"""
    leave = get_object_or_404(Leave, pk=pk)
    
    # Check if user is authorized to view this leave
    if not request.user.is_employer and request.user != leave.employee:
        messages.error(request, "You don't have permission to view this leave request.")
        return redirect('attendance:index')
    
    # Calculate duration
    duration = leave.get_business_days()
    
    context = {
        'leave': leave,
        'duration': duration
    }
    
    return render(request, 'attendance/leave_detail.html', context)

@login_required
def leave_balance(request):
    """View current leave balance"""
    try:
        leave_balance = LeaveBalance.objects.get(employee=request.user)
    except LeaveBalance.DoesNotExist:
        leave_balance = LeaveBalance.objects.create(
            employee=request.user,
            casual_leave=get_policy_value('default_casual_leaves', 12),
            sick_leave=get_policy_value('default_sick_leaves', 10)
        )
    
    # Get leave history for the current year
    current_year = timezone.now().year
    approved_leaves = Leave.objects.filter(
        employee=request.user,
        status=Leave.APPROVED,
        start_date__year=current_year
    ).select_related('leave_type')
    
    casual_leaves_taken = [leave for leave in approved_leaves if leave.leave_type.name.lower() == 'casual leave']
    sick_leaves_taken = [leave for leave in approved_leaves if leave.leave_type.name.lower() == 'sick leave']
    
    casual_days_taken = sum([leave.get_business_days() for leave in casual_leaves_taken])
    sick_days_taken = sum([leave.get_business_days() for leave in sick_leaves_taken])
    
    context = {
        'leave_balance': leave_balance,
        'casual_leaves_taken': casual_leaves_taken,
        'sick_leaves_taken': sick_leaves_taken,
        'casual_days_taken': casual_days_taken,
        'sick_days_taken': sick_days_taken,
        'current_year': current_year
    }
    
    return render(request, 'attendance/leave_balance.html', context)

# Employer/Admin Views
@login_required
def attendance_approvals(request):
    """View and manage attendance approval requests"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('attendance:index')
    
    # Get filter parameters
    status_filter = request.GET.get('status', Attendance.PENDING)
    date_filter = request.GET.get('date')
    
    # Query attendance records
    attendance_query = Attendance.objects.all()
    
    if status_filter:
        attendance_query = attendance_query.filter(status=status_filter)
    
    if date_filter:
        try:
            date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()
            attendance_query = attendance_query.filter(date=date_filter)
        except ValueError:
            messages.warning(request, "Invalid date format. Showing all dates.")
    
    # Order by most recent first
    attendance_records = attendance_query.select_related('employee').order_by('-date', '-created_at')
    
    # Paginate results
    paginator = Paginator(attendance_records, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter
    }
    
    return render(request, 'attendance/attendance_approval.html', context)

@login_required
def attendance_approval_detail(request, pk):
    """View details of an attendance record"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('attendance:index')
    
    attendance = get_object_or_404(Attendance, pk=pk)
    
    # Calculate duration if checked out
    duration = None
    if attendance.check_out:
        duration = attendance.get_duration()
    
    # Check if employee was late
    is_late = attendance.is_late()
    
    context = {
        'attendance': attendance,
        'duration': duration,
        'is_late': is_late
    }
    
    return render(request, 'attendance/attendance_approval_detail.html', context)

@login_required
def approve_attendance(request, pk):
    """Approve an attendance request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to approve attendance.")
        return redirect('attendance:index')
    
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if attendance.status != Attendance.PENDING:
        messages.warning(request, "This attendance record has already been processed.")
        return redirect('attendance:attendance_approval_detail', pk=pk)
    
    if request.method == 'POST':
        attendance.status = Attendance.APPROVED
        attendance.approved_by = request.user
        attendance.save()
        
        # Notify the employee
        Notification.create_notification(
            user=attendance.employee,
            title="Attendance Approved",
            message=f"Your attendance for {attendance.date} has been approved.",
            notification_type=Notification.ATTENDANCE
        )
        
        messages.success(request, f"Attendance for {attendance.employee.get_full_name() or attendance.employee.username} on {attendance.date} has been approved.")
        return redirect('attendance:attendance_approvals')
    
    return render(request, 'attendance/approve_attendance.html', {'attendance': attendance})

@login_required
def reject_attendance(request, pk):
    """Reject an attendance request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to reject attendance.")
        return redirect('attendance:index')
    
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if attendance.status != Attendance.PENDING:
        messages.warning(request, "This attendance record has already been processed.")
        return redirect('attendance:attendance_approval_detail', pk=pk)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        attendance.status = Attendance.REJECTED
        attendance.approved_by = request.user
        attendance.rejection_reason = rejection_reason
        attendance.save()
        
        # Notify the employee
        Notification.create_notification(
            user=attendance.employee,
            title="Attendance Rejected",
            message=f"Your attendance for {attendance.date} has been rejected.",
            notification_type=Notification.ATTENDANCE
        )
        
        messages.success(request, f"Attendance for {attendance.employee.get_full_name() or attendance.employee.username} on {attendance.date} has been rejected.")
        return redirect('attendance:attendance_approvals')
    
    return render(request, 'attendance/reject_attendance.html', {'attendance': attendance})

@login_required
def leave_approvals(request):
    """View and manage leave approval requests"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('attendance:index')
    
    # Get filter parameters
    status_filter = request.GET.get('status', Leave.PENDING)
    
    # Query leave requests
    leave_query = Leave.objects.all()
    
    if status_filter:
        leave_query = leave_query.filter(status=status_filter)
    
    # Order by most recent first
    leave_requests = leave_query.select_related('employee', 'leave_type').order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(leave_requests, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter
    }
    
    return render(request, 'attendance/leave_approval.html', context)

@login_required
def leave_approval_detail(request, pk):
    """View details of a leave request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('attendance:index')
    
    leave = get_object_or_404(Leave, pk=pk)
    
    # Calculate duration
    duration = leave.get_business_days()
    
    # Get employee's leave balance
    try:
        leave_balance = LeaveBalance.objects.get(employee=leave.employee)
    except LeaveBalance.DoesNotExist:
        leave_balance = None
    
    context = {
        'leave': leave,
        'duration': duration,
        'leave_balance': leave_balance
    }
    
    return render(request, 'attendance/leave_approval_detail.html', context)

@login_required
def approve_leave(request, pk):
    """Approve a leave request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to approve leave requests.")
        return redirect('attendance:index')
    
    leave = get_object_or_404(Leave, pk=pk)
    
    if leave.status != Leave.PENDING:
        messages.warning(request, "This leave request has already been processed.")
        return redirect('attendance:leave_approval_detail', pk=pk)
    
    # Get leave balance
    try:
        leave_balance = LeaveBalance.objects.get(employee=leave.employee)
    except LeaveBalance.DoesNotExist:
        leave_balance = LeaveBalance.objects.create(
            employee=leave.employee,
            casual_leave=get_policy_value('default_casual_leaves', 12),
            sick_leave=get_policy_value('default_sick_leaves', 10)
        )
    
    # Calculate duration
    duration = leave.get_business_days()
    
    if request.method == 'POST':
        # Update leave request
        leave.status = Leave.APPROVED
        leave.approved_by = request.user
        leave.save()
        
        # Update leave balance
        leave_balance.update_balance(leave.leave_type.name, duration)
        
        # Notify the employee
        Notification.create_notification(
            user=leave.employee,
            title="Leave Request Approved",
            message=f"Your leave request from {leave.start_date} to {leave.end_date} has been approved.",
            notification_type=Notification.ATTENDANCE
        )
        
        messages.success(request, f"Leave request for {leave.employee.get_full_name() or leave.employee.username} has been approved.")
        return redirect('attendance:leave_approvals')
    
    context = {
        'leave': leave,
        'duration': duration,
        'leave_balance': leave_balance
    }
    
    return render(request, 'attendance/approve_leave.html', context)

@login_required
def reject_leave(request, pk):
    """Reject a leave request"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to reject leave requests.")
        return redirect('attendance:index')
    
    leave = get_object_or_404(Leave, pk=pk)
    
    if leave.status != Leave.PENDING:
        messages.warning(request, "This leave request has already been processed.")
        return redirect('attendance:leave_approval_detail', pk=pk)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')
        
        leave.status = Leave.REJECTED
        leave.approved_by = request.user
        leave.rejection_reason = rejection_reason
        leave.save()
        
        # Notify the employee
        Notification.create_notification(
            user=leave.employee,
            title="Leave Request Rejected",
            message=f"Your leave request from {leave.start_date} to {leave.end_date} has been rejected.",
            notification_type=Notification.ATTENDANCE
        )
        
        messages.success(request, f"Leave request for {leave.employee.get_full_name() or leave.employee.username} has been rejected.")
        return redirect('attendance:leave_approvals')
    
    return render(request, 'attendance/reject_leave.html', {'leave': leave})

@login_required
def attendance_reports(request):
    """Generate attendance reports"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to access reports.")
        return redirect('attendance:index')
    
    # Get filter parameters
    employee_id = request.GET.get('employee')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Default to current month if no date range specified
    if not start_date:
        start_date = timezone.now().replace(day=1).date().strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().date().strftime('%Y-%m-%d')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        start_date = timezone.now().replace(day=1).date()
        end_date = timezone.now().date()
    
    # Query attendance records
    attendance_query = Attendance.objects.filter(
        date__range=[start_date, end_date],
        status=Attendance.APPROVED
    )
    
    if employee_id:
        attendance_query = attendance_query.filter(employee_id=employee_id)
    
    attendance_records = attendance_query.select_related('employee').order_by('employee__username', 'date')
    
    # Get employees for filter dropdown
    employees = User.objects.filter(userprofile__role=UserProfile.EMPLOYEE).order_by('username')
    
    # Calculate statistics
    stats = {}
    for record in attendance_records:
        employee_name = record.employee.get_full_name() or record.employee.username
        if employee_name not in stats:
            stats[employee_name] = {
                'days': 0,
                'hours': 0,
                'late_days': 0,
            }
        
        stats[employee_name]['days'] += 1
        
        if record.check_out:
            duration = record.get_duration()
            if duration:
                stats[employee_name]['hours'] += duration
        
        if record.is_late():
            stats[employee_name]['late_days'] += 1
    
    context = {
        'attendance_records': attendance_records,
        'employees': employees,
        'start_date': start_date,
        'end_date': end_date,
        'employee_id': employee_id,
        'stats': stats
    }
    
    return render(request, 'attendance/reports.html', context)

@login_required
def manage_policies(request):
    """View and manage attendance policies"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to access policies.")
        return redirect('attendance:index')
    
    policies = Policy.objects.all().order_by('name')
    
    return render(request, 'attendance/manage_policies.html', {'policies': policies})

@login_required
def create_policy(request):
    """Create a new attendance policy"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to create policies.")
        return redirect('attendance:index')
    
    if request.method == 'POST':
        form = PolicyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy created successfully.")
            return redirect('attendance:manage_policies')
    else:
        form = PolicyForm()
    
    return render(request, 'attendance/policy_form.html', {
        'form': form,
        'title': 'Create New Policy'
    })

@login_required
def edit_policy(request, pk):
    """Edit an existing attendance policy"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to edit policies.")
        return redirect('attendance:index')
    
    policy = get_object_or_404(Policy, pk=pk)
    
    if request.method == 'POST':
        form = PolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Policy updated successfully.")
            return redirect('attendance:manage_policies')
    else:
        form = PolicyForm(instance=policy)
    
    return render(request, 'attendance/policy_form.html', {
        'form': form,
        'policy': policy,
        'title': 'Edit Policy'
    })

@login_required
def delete_policy(request, pk):
    """Delete an attendance policy"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to delete policies.")
        return redirect('attendance:index')
    
    policy = get_object_or_404(Policy, pk=pk)
    
    if request.method == 'POST':
        policy_name = policy.name
        policy.delete()
        messages.success(request, f"Policy '{policy_name}' deleted successfully.")
        return redirect('attendance:manage_policies')
    
    return render(request, 'attendance/delete_policy.html', {'policy': policy})

@login_required
def export_attendance(request):
    """Export attendance data for employers"""
    if not request.user.is_employer:
        messages.error(request, "You don't have permission to export attendance data.")
        return redirect('attendance:index')
    
    # Get filter parameters
    employee_id = request.GET.get('employee')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('format', 'excel')
    
    # Default to current month if no date range specified
    if not start_date:
        start_date = timezone.now().replace(day=1).date().strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().date().strftime('%Y-%m-%d')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('attendance:attendance_reports')
    
    # Query attendance records
    attendance_query = Attendance.objects.filter(
        date__range=[start_date, end_date]
    )
    
    if employee_id:
        attendance_query = attendance_query.filter(employee_id=employee_id)
    
    attendance_records = attendance_query.select_related('employee').order_by('employee__username', 'date')
    
    if export_format == 'pdf':
        # Generate PDF report
        filename = f"attendance_report_{start_date}_{end_date}.pdf"
        pdf_data = generate_attendance_report_pdf(attendance_records, start_date, end_date)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_data)
        return response
    else:
        # Generate Excel report
        filename = f"attendance_report_{start_date}_{end_date}.xlsx"
        excel_data = generate_attendance_report_excel(attendance_records, start_date, end_date)
        
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

@login_required
def export_my_attendance(request):
    """Export personal attendance data for employees"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('format', 'excel')
    
    # Default to current month if no date range specified
    if not start_date:
        start_date = timezone.now().replace(day=1).date().strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().date().strftime('%Y-%m-%d')
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Invalid date format.")
        return redirect('attendance:attendance_history')
    
    # Query attendance records
    attendance_records = Attendance.objects.filter(
        employee=request.user,
        date__range=[start_date, end_date]
    ).order_by('date')
    
    if export_format == 'pdf':
        # Generate PDF report
        filename = f"my_attendance_{start_date}_{end_date}.pdf"
        pdf_data = generate_attendance_report_pdf(attendance_records, start_date, end_date)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_data)
        return response
    else:
        # Generate Excel report
        filename = f"my_attendance_{start_date}_{end_date}.xlsx"
        excel_data = generate_attendance_report_excel(attendance_records, start_date, end_date)
        
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

# API endpoints for HTMX
@login_required
def check_attendance_status(request):
    """Check attendance status for the current day (HTMX endpoint)"""
    today = timezone.now().date()
    
    try:
        attendance = Attendance.objects.get(employee=request.user, date=today)
        context = {
            'checked_in': True,
            'attendance': attendance
        }
    except Attendance.DoesNotExist:
        context = {
            'checked_in': False,
            'attendance': None
        }
    
    if request.headers.get('HX-Request'):
        return render(request, 'attendance/partials/attendance_status.html', context)
    return JsonResponse(context)

@login_required
def today_attendance_stats(request):
    """Get today's attendance statistics (HTMX endpoint)"""
    if not request.user.is_employer:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    today = timezone.now().date()
    today_attendance = Attendance.objects.filter(date=today)
    total_employees = User.objects.filter(userprofile__role=UserProfile.EMPLOYEE).count()
    
    # Today's stats
    present_count = today_attendance.filter(status=Attendance.APPROVED).count()
    pending_count = today_attendance.filter(status=Attendance.PENDING).count()
    absent_count = total_employees - present_count - pending_count
    
    context = {
        'present_count': present_count,
        'pending_count': pending_count,
        'absent_count': absent_count,
        'total_employees': total_employees,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'attendance/partials/today_stats.html', context)
    return JsonResponse(context)
