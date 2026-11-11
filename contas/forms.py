from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Usuario


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Esta conta está desativada. Procure um administrador.",
    }


class UsuarioForm(forms.ModelForm):
    """Cadastro/edição de usuário feito por um administrador."""

    senha = forms.CharField(
        label="Senha",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Na edição, deixe em branco para manter a senha atual.",
    )

    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "perfil", "is_active"]
        labels = {
            "username": "Usuário (login)",
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "perfil": "Perfil de acesso",
            "is_active": "Conta ativa",
        }
        help_texts = {"username": "", "is_active": ""}

    def __init__(self, *args, usuario_logado=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_logado = usuario_logado
        self.fields["first_name"].required = True
        if not self.instance.pk:
            self.fields["senha"].required = True
            self.fields["senha"].help_text = ""

    def clean_senha(self):
        senha = self.cleaned_data.get("senha")
        if senha:
            password_validation.validate_password(senha, self.instance)
        return senha

    def clean(self):
        dados = super().clean()
        if self.instance.pk and self.usuario_logado and self.instance.pk == self.usuario_logado.pk:
            if not dados.get("is_active"):
                self.add_error("is_active", "Você não pode desativar a própria conta.")
            if dados.get("perfil") != Usuario.Perfil.ADMIN:
                self.add_error("perfil", "Você não pode remover o próprio perfil de administrador.")
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get("senha"):
            usuario.set_password(self.cleaned_data["senha"])
        if commit:
            usuario.save()
        return usuario


class MeusDadosForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Nome", "last_name": "Sobrenome", "email": "E-mail"}
