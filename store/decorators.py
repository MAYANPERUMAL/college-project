from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in with an Administrator account to access that page.")
            return redirect('login')
        if not request.user.is_admin_user():
            messages.error(request, "Access Denied: You do not have administrator permissions to view this page.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def seller_required(view_func):
    """
    Enforces that the user is authenticated and is either a Seller or an Admin.
    Strictly denies customers access to seller portal and management actions.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please sign in with a Seller account to access the Seller Portal.")
            return redirect('login')
        if not (request.user.is_seller_user() or request.user.is_admin_user()):
            messages.error(request, "Access Denied: You do not have Seller permissions to access this page.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def delivery_required(view_func):
    """
    Enforces that the user is authenticated and is either a Delivery Partner or an Admin.
    Strictly denies customers and unassigned users.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please sign in with a Delivery Partner account to access the Delivery Portal.")
            return redirect('login')
        if not (request.user.is_delivery_partner() or request.user.is_admin_user()):
            messages.error(request, "Access Denied: You do not have Delivery Partner permissions.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
