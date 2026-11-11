"""Código de barras Code 128 (o mesmo do DANFE) da chave de acesso, em SVG."""
from barcode import Code128
from django.utils.safestring import mark_safe


def svg_chave(chave: str, altura: int = 56) -> str:
    if not chave:
        return ""
    modulos = Code128(chave).build()[0]  # sequência de "1" (barra) e "0" (espaço)
    margem = 10
    largura = len(modulos) + 2 * margem
    barras, i = [], 0
    while i < len(modulos):
        if modulos[i] == "1":
            j = i
            while j < len(modulos) and modulos[j] == "1":
                j += 1
            barras.append(f'<rect x="{margem + i}" y="0" width="{j - i}" height="{altura}"/>')
            i = j
        else:
            i += 1
    return mark_safe(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'preserveAspectRatio="none" role="img" aria-label="Código de barras da chave de acesso" '
        f'fill="#000" shape-rendering="crispEdges">{"".join(barras)}</svg>'
    )
