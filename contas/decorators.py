from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view):
    """Exige usuário autenticado com perfil Administrador."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.eh_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def superuser_required(view):
    """Exige usuário autenticado que seja superusuário (não basta o perfil Administrador)."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
