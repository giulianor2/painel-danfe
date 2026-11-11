from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "contas"

urlpatterns = [
    path("entrar/", views.EntrarView.as_view(), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
    path("minha-conta/", views.minha_conta, name="minha_conta"),
    path("usuarios/", views.usuarios_lista, name="usuarios"),
    path("usuarios/novo/", views.usuario_novo, name="usuario_novo"),
    path("usuarios/<int:pk>/", views.usuario_editar, name="usuario_editar"),
]
