from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import admin_required
from .forms import LoginForm, MeusDadosForm, UsuarioForm
from .models import Usuario


class EntrarView(LoginView):
    template_name = "contas/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        # "Manter conectado" desmarcado: a sessão termina ao fechar o navegador.
        if not self.request.POST.get("lembrar"):
            self.request.session.set_expiry(0)
        return super().form_valid(form)


@login_required
def minha_conta(request):
    dados_form = MeusDadosForm(instance=request.user, prefix="dados")
    senha_form = PasswordChangeForm(request.user, prefix="senha")
    if request.method == "POST":
        if request.POST.get("acao") == "senha":
            senha_form = PasswordChangeForm(request.user, request.POST, prefix="senha")
            if senha_form.is_valid():
                senha_form.save()
                update_session_auth_hash(request, senha_form.user)
                messages.success(request, "Senha alterada com sucesso.")
                return redirect("contas:minha_conta")
        else:
            dados_form = MeusDadosForm(request.POST, instance=request.user, prefix="dados")
            if dados_form.is_valid():
                dados_form.save()
                messages.success(request, "Dados atualizados.")
                return redirect("contas:minha_conta")
    return render(request, "contas/minha_conta.html", {"dados_form": dados_form, "senha_form": senha_form})


@admin_required
def usuarios_lista(request):
    q = request.GET.get("q", "").strip()
    usuarios = Usuario.objects.all()
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    return render(request, "contas/usuarios_lista.html", {"usuarios": usuarios, "q": q})


@admin_required
def usuario_novo(request):
    form = UsuarioForm(request.POST or None, usuario_logado=request.user)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        messages.success(request, f"Usuário {usuario.username} criado.")
        return redirect("contas:usuarios")
    return render(request, "contas/usuario_form.html", {"form": form, "titulo": "Novo usuário"})


@admin_required
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario, usuario_logado=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        if usuario.pk == request.user.pk and form.cleaned_data.get("senha"):
            update_session_auth_hash(request, usuario)
        messages.success(request, f"Usuário {usuario.username} atualizado.")
        return redirect("contas:usuarios")
    return render(request, "contas/usuario_form.html", {"form": form, "titulo": "Editar usuário", "editado": usuario})
