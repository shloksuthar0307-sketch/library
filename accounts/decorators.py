from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps
from django.contrib import messages

def role_required(allowed_roles):
    """
    Decorator for views that checks whether a user has a particular role,
    redirecting to the access denied page or raising PermissionDenied if necessary.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
                
            if request.user.role in allowed_roles or request.user.is_superadmin():
                return view_func(request, *args, **kwargs)
                
            # If not allowed, redirect to 403 or custom forbidden
            messages.error(request, "You do not have permission to access this resource.")
            return redirect('accounts:forbidden') # We will create a forbidden view
            
        return _wrapped_view
    return decorator

