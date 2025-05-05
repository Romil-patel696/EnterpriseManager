from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, UserProfileForm, EmployeeRegistrationForm
from .models import UserProfile, User
from django.contrib.auth import login
from django.http import HttpResponseForbidden

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Get the role before saving the user
            role = form.cleaned_data.get('role')
            
            # Save user without saving m2m fields
            user = form.save(commit=False)
            
            # Set staff status for employers
            if role == UserProfile.EMPLOYER:
                user.is_staff = True
            
            # Save the user to create the instance in the database
            user.save()
            
            # Force save form's m2m fields
            form.save_m2m()
            
            # Check if userprofile exists, create if it doesn't
            try:
                profile = user.userprofile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=user)
            
            # Update the profile with role
            profile.role = role
            profile.save()
            
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('core:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    user = request.user
    return render(request, 'accounts/profile.html', {'user': user})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        profile_form = UserProfileForm(instance=request.user.userprofile)
    
    return render(request, 'accounts/edit_profile.html', {
        'profile_form': profile_form
    })

@login_required
def register_employee(request):
    """View for employers to register their employees"""
    # Check if user is an employer
    if not request.user.is_employer:
        messages.error(request, 'Only employers can register employees.')
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            # Save user without saving m2m fields
            employee = form.save(commit=False)
            employee.save()
            
            # Extract profile data from form
            department = form.cleaned_data.get('department')
            position = form.cleaned_data.get('position')
            phone = form.cleaned_data.get('phone')
            
            # Check if userprofile exists, create if it doesn't
            try:
                profile = employee.userprofile
            except UserProfile.DoesNotExist:
                profile = UserProfile.objects.create(user=employee)
            
            # Update the profile with role and employer
            profile.role = UserProfile.EMPLOYEE
            profile.employer = request.user
            profile.department = department
            profile.position = position
            profile.phone = phone
            profile.save()
            
            messages.success(request, f'Employee {employee.username} has been registered successfully!')
            return redirect('accounts:employee_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EmployeeRegistrationForm()
    
    return render(request, 'accounts/register_employee.html', {'form': form})

@login_required
def employee_list(request):
    """View for employers to see their employees"""
    # Check if user is an employer
    if not request.user.is_employer:
        messages.error(request, 'Only employers can view employees.')
        return HttpResponseForbidden()
    
    # Get all employees of this employer
    employees = User.objects.filter(
        userprofile__employer=request.user,
        userprofile__role=UserProfile.EMPLOYEE
    ).select_related('userprofile')
    
    return render(request, 'accounts/employee_list.html', {
        'employees': employees
    })

@login_required
def employee_detail(request, employee_id):
    """View for employers to see employee details"""
    # Check if user is an employer
    if not request.user.is_employer:
        messages.error(request, 'Only employers can view employee details.')
        return HttpResponseForbidden()
    
    # Get the employee if it belongs to this employer
    employee = get_object_or_404(
        User, 
        id=employee_id,
        userprofile__employer=request.user,
        userprofile__role=UserProfile.EMPLOYEE
    )
    
    return render(request, 'accounts/employee_detail.html', {
        'employee': employee
    })
