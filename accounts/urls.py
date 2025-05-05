from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import LoginForm, CustomPasswordResetForm, CustomSetPasswordForm

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=LoginForm
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('register/', views.register, name='register'),
    
    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        form_class=CustomPasswordResetForm,
        email_template_name='accounts/password_reset_email.html',
        success_url='/accounts/password-reset/done/'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=CustomSetPasswordForm,
        success_url='/accounts/password-reset-complete/'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Employee management URLs
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/register/', views.register_employee, name='register_employee'),
    path('employees/<int:employee_id>/', views.employee_detail, name='employee_detail'),
]
