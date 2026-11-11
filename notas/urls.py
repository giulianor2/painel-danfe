from django.urls import path

from . import views

app_name = "notas"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("notas/<int:pk>/", views.detalhe, name="detalhe"),
    path("notas/<int:pk>/pdf/", views.pdf, name="pdf"),
    path("notas/<int:pk>/reler/", views.reler, name="reler"),
    path("estatisticas/", views.estatisticas, name="estatisticas"),
    path("importacao/", views.importacao, name="importacao"),
    path("importacao/apagar-todas/", views.apagar_todas, name="apagar_todas"),
]
