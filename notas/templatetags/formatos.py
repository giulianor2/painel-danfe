from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def moeda(valor):
    """1234.5 -> R$ 1.234,50"""
    if valor in (None, ""):
        return "—"
    texto = f"{Decimal(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@register.filter
def cnpj_cpf(valor):
    v = "".join(c for c in str(valor or "") if c.isdigit())
    if len(v) == 14:
        return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
    if len(v) == 11:
        return f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
    return valor or "—"


@register.filter
def cep(valor):
    v = str(valor or "")
    return f"{v[:5]}-{v[5:]}" if len(v) == 8 else (v or "—")


@register.filter
def chave(valor):
    v = str(valor or "")
    return " ".join(v[i : i + 4] for i in range(0, len(v), 4)) if v else "—"


@register.filter
def ou_traco(valor):
    return valor if valor not in (None, "") else "—"


@register.simple_tag(takes_context=True)
def url_com(context, **novos):
    """Monta a querystring atual trocando/adicionando parâmetros (paginação e ordenação)."""
    params = context["request"].GET.copy()
    for chave_param, valor in novos.items():
        if valor in (None, ""):
            params.pop(chave_param, None)
        else:
            params[chave_param] = valor
    return "?" + params.urlencode()


@register.simple_tag(takes_context=True)
def ordenar(context, campo):
    """Link de ordenação da coluna: alterna crescente/decrescente."""
    novo = f"-{campo}" if context.get("ordem") == campo else campo
    return url_com(context, ordem=novo, pagina=None)


@register.simple_tag(takes_context=True)
def seta(context, campo):
    atual = context.get("ordem", "")
    if atual == campo:
        return "↑"
    if atual == f"-{campo}":
        return "↓"
    return ""
