from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, UserProfileForm
from .models import UserProfile
from django.contrib.auth import login

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
