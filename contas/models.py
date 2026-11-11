from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema com perfil de acesso."""

    class Perfil(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        CONSULTA = "CONSULTA", "Consulta"

    perfil = models.CharField(max_length=10, choices=Perfil.choices, default=Perfil.CONSULTA)

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["first_name", "username"]

    def save(self, *args, **kwargs):
        # Superusuários (createsuperuser) são sempre administradores do painel.
        if self.is_superuser:
            self.perfil = self.Perfil.ADMIN
        super().save(*args, **kwargs)

    @property
    def eh_admin(self):
        return self.perfil == self.Perfil.ADMIN

    @property
    def nome_exibicao(self):
        return self.get_full_name() or self.username

    @property
    def iniciais(self):
        partes = self.nome_exibicao.split()
        return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()
