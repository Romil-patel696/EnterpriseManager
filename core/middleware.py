from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class RoleBasedAccessMiddleware:
    """Middleware to restrict access based on user role"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process the request
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Called just before Django calls the view.
        Return None to continue processing, or return a HttpResponse to short-circuit.
        """
        # Skip middleware for these views
        exempt_views = [
            'login', 'logout', 'register', 'password_reset', 
            'password_reset_done', 'password_reset_confirm', 
            'password_reset_complete', 'index'
        ]
        
        # Get the view name
        view_name = view_func.__name__
        
        # Allow access to exempt views
        if view_name in exempt_views or not request.user.is_authenticated:
            return None
        
        # Restrict admin views to employers
        if 'admin' in request.path and not getattr(request.user, 'is_employer', False):
            messages.error(request, "You don't have permission to access this area.")
            return redirect(reverse('core:dashboard'))
        
        # Employer-only URLs
        if any(url in request.path for url in ['/approval/', '/analytics/', '/management/']):
            if not getattr(request.user, 'is_employer', False):
                messages.error(request, "This area is restricted to employers only.")
                return redirect(reverse('core:dashboard'))
        
        # Continue with the request
        return None
