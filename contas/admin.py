from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "perfil", "is_active")
    list_filter = ("perfil", "is_active")
    fieldsets = UserAdmin.fieldsets + (("Painel DANFE", {"fields": ("perfil",)}),)
