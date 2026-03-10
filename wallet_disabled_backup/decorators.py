from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(view_func):
    """
    Decorator để chỉ cho phép admin truy cập
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if request.user.account_type != 'admin':
            messages.error(request, 'Bạn không có quyền truy cập tính năng này. Chỉ Admin mới có thể quản lý ví.')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
