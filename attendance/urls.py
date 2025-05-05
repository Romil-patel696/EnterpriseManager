from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Main attendance views
    path('', views.index, name='index'),
    
    # Employee attendance views
    path('request/', views.attendance_request, name='request'),
    path('history/', views.attendance_history, name='history'),
    path('leave/request/', views.leave_request, name='leave_request'),
    path('leave/history/', views.leave_history, name='leave_history'),
    path('leave/<int:pk>/', views.leave_detail, name='leave_detail'),
    path('leave/balance/', views.leave_balance, name='leave_balance'),
    
    # Employer/Admin views
    path('admin/approvals/', views.attendance_approvals, name='attendance_approvals'),
    path('admin/approvals/<int:pk>/', views.attendance_approval_detail, name='attendance_approval_detail'),
    path('admin/approvals/<int:pk>/approve/', views.approve_attendance, name='approve_attendance'),
    path('admin/approvals/<int:pk>/reject/', views.reject_attendance, name='reject_attendance'),
    
    path('admin/leave-approvals/', views.leave_approvals, name='leave_approvals'),
    path('admin/leave-approvals/<int:pk>/', views.leave_approval_detail, name='leave_approval_detail'),
    path('admin/leave-approvals/<int:pk>/approve/', views.approve_leave, name='approve_leave'),
    path('admin/leave-approvals/<int:pk>/reject/', views.reject_leave, name='reject_leave'),
    
    path('admin/reports/', views.attendance_reports, name='attendance_reports'),
    path('admin/policies/', views.manage_policies, name='manage_policies'),
    path('admin/policies/create/', views.create_policy, name='create_policy'),
    path('admin/policies/<int:pk>/edit/', views.edit_policy, name='edit_policy'),
    path('admin/policies/<int:pk>/delete/', views.delete_policy, name='delete_policy'),
    
    # Data export
    path('export/', views.export_attendance, name='export_attendance'),
    path('export/my/', views.export_my_attendance, name='export_my_attendance'),
    
    # API endpoints for HTMX
    path('api/check-status/', views.check_attendance_status, name='check_attendance_status'),
    path('api/today-stats/', views.today_attendance_stats, name='today_attendance_stats'),
]
