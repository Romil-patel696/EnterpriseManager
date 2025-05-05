from django import forms
from django.utils import timezone
from .models import Attendance, Leave, LeaveType, Policy

class AttendanceRequestForm(forms.ModelForm):
    """Form for attendance check-in/check-out requests"""
    
    class Meta:
        model = Attendance
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Any comments or notes about your attendance today'
            }),
        }

class LeaveRequestForm(forms.ModelForm):
    """Form for leave requests"""
    
    class Meta:
        model = Leave
        fields = ['leave_type', 'start_date', 'end_date', 'day_type', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'day_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Reason for requesting leave'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Start date validation
        if start_date:
            today = timezone.now().date()
            if start_date < today:
                self.add_error('start_date', 'Start date cannot be in the past')
        
        # End date validation
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'End date cannot be before start date')
        
        return cleaned_data

class LeaveApprovalForm(forms.ModelForm):
    """Form for approving/rejecting leave requests"""
    
    class Meta:
        model = Leave
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Reason for rejection (if applicable)'
            }),
        }

class AttendanceApprovalForm(forms.ModelForm):
    """Form for approving/rejecting attendance"""
    
    class Meta:
        model = Attendance
        fields = ['rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Reason for rejection (if applicable)'
            }),
        }

class PolicyForm(forms.ModelForm):
    """Form for creating/editing attendance policies"""
    
    class Meta:
        model = Policy
        fields = ['name', 'value', 'data_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.TextInput(attrs={'class': 'form-control'}),
            'data_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        # Convert to lowercase and replace spaces with underscores
        name = name.lower().replace(' ', '_')
        
        # Check for existing policy with same name (if creating new policy)
        if not self.instance.pk:
            if Policy.objects.filter(name=name).exists():
                raise forms.ValidationError('A policy with this name already exists')
        
        return name

class AttendanceReportForm(forms.Form):
    """Form for filtering attendance reports"""
    employee = forms.ModelChoiceField(
        queryset=None,  # Set dynamically in view
        required=False,
        empty_label="All Employees",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    export_format = forms.ChoiceField(
        choices=[('excel', 'Excel'), ('pdf', 'PDF')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        from accounts.models import User, UserProfile
        super().__init__(*args, **kwargs)
        # Set employee queryset
        self.fields['employee'].queryset = User.objects.filter(
            userprofile__role=UserProfile.EMPLOYEE
        ).order_by('username')
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date")
        
        return cleaned_data
