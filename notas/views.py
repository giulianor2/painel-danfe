from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import admin_required, superuser_required

from .barras import svg_chave
from .importador import apagar_notas
from .models import Emitente, NotaFiscal, Sincronizacao

ORDENS = {
    "numero": "numero",
    "emissao": "data_emissao",
    "emitente": "emitente__razao_social",
    "destinatario": "dest_nome",
    "total": "valor_total",
}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _data_param(texto):
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _filtrar(request, notas):
    """Aplica os filtros da barra de pesquisa. Devolve (queryset, filtros usados)."""
    f = {
        "q": request.GET.get("q", "").strip(),
        "emitente": request.GET.get("emitente", ""),
        "status": request.GET.get("status", ""),
        "tipo": request.GET.get("tipo", ""),
        "de": request.GET.get("de", ""),
        "ate": request.GET.get("ate", ""),
    }
    if f["q"]:
        digitos = "".join(ch for ch in f["q"] if ch.isdigit())
        cond = (
            Q(emitente__razao_social__icontains=f["q"])
            | Q(dest_nome__icontains=f["q"])
            | Q(natureza_operacao__icontains=f["q"])
            | Q(arquivo__icontains=f["q"])
            | Q(discriminacao__icontains=f["q"])
            | Q(codigo_verificacao__iexact=f["q"])
        )
        if digitos:
            cond |= Q(chave_acesso__icontains=digitos) | Q(emitente__cnpj__icontains=digitos)
            if len(digitos) <= 9:
                cond |= Q(numero=int(digitos))
        notas = notas.filter(cond)
    if f["emitente"].isdigit():
        notas = notas.filter(emitente_id=f["emitente"])
    if f["tipo"] in NotaFiscal.Tipo.values:
        notas = notas.filter(tipo_documento=f["tipo"])
    if f["status"] in NotaFiscal.Status.values:
        notas = notas.filter(status=f["status"])
    if de := _data_param(f["de"]):
        notas = notas.filter(data_emissao__gte=de)
    if ate := _data_param(f["ate"]):
        notas = notas.filter(data_emissao__lte=ate)
    return notas, f


@login_required
def painel(request):
    todas = NotaFiscal.objects.select_related("emitente")
    notas, filtros = _filtrar(request, todas)

    ordem = request.GET.get("ordem", "-emissao")
    campo = ORDENS.get(ordem.lstrip("-"))
    if campo:
        notas = notas.order_by(("-" if ordem.startswith("-") else "") + campo, "-id")
    else:
        ordem = "-emissao"

    validas = notas.exclude(status=NotaFiscal.Status.ERRO)
    resumo = validas.aggregate(qtd=Count("id"), total=Sum("valor_total"), emitentes=Count("emitente", distinct=True))
    pagina = Paginator(notas, 15).get_page(request.GET.get("pagina"))
    return render(
        request,
        "notas/painel.html",
        {
            "pagina": pagina,
            "filtros": filtros,
            "tem_filtro": any(filtros.values()),
            "ordem": ordem,
            "resumo": resumo,
            "com_problema": todas.exclude(status=NotaFiscal.Status.OK).count(),
            "emitentes": Emitente.objects.all(),
            "status_opcoes": NotaFiscal.Status.choices,
            "tipo_opcoes": NotaFiscal.Tipo.choices,
            "ultima_sinc": Sincronizacao.objects.first(),
            "ultima_nota": todas.order_by("-importado_em").first(),
        },
    )


@login_required
def detalhe(request, pk):
    nota = get_object_or_404(NotaFiscal.objects.select_related("emitente"), pk=pk)
    return render(request, "notas/detalhe.html", {"nota": nota, "barras": svg_chave(nota.chave_acesso)})


@login_required
def pdf(request, pk):
    """Abre o PDF original, sem expor a pasta diretamente."""
    nota = get_object_or_404(NotaFiscal, pk=pk)
    pasta = Path(settings.DANFE_PASTA).resolve()
    caminho = (pasta / nota.arquivo).resolve()
    if pasta not in caminho.parents or not caminho.is_file():
        raise Http404("Arquivo não está mais na pasta.")
    return FileResponse(caminho.open("rb"), content_type="application/pdf", filename=caminho.name)


@admin_required
@require_POST
def reler(request, pk):
    """Descarta o registro; o arquivo será lido de novo na próxima varredura da pasta."""
    nota = get_object_or_404(NotaFiscal, pk=pk)
    arquivo = nota.arquivo
    nota.delete()
    messages.success(request, f"{arquivo} será lido novamente na próxima verificação da pasta.")
    return redirect("notas:painel")


@superuser_required
@require_POST
def apagar_todas(request):
    """Apaga todas as notas do banco; a pasta é lida do zero na próxima varredura."""
    if request.POST.get("confirmacao", "").strip().upper() != "APAGAR":
        messages.error(request, "Nada foi apagado. Para confirmar, digite APAGAR no campo ao lado do botão.")
        return redirect("notas:importacao")
    r = apagar_notas()
    messages.success(
        request,
        f"{r['notas']} nota(s) e {r['emitentes']} emitente(s) apagados. "
        "Os PDFs da pasta serão importados de novo na próxima verificação.",
    )
    return redirect("notas:importacao")


@login_required
def estatisticas(request):
    notas = NotaFiscal.objects.exclude(status=NotaFiscal.Status.ERRO)
    de, ate = _data_param(request.GET.get("de")), _data_param(request.GET.get("ate"))
    if de:
        notas = notas.filter(data_emissao__gte=de)
    if ate:
        notas = notas.filter(data_emissao__lte=ate)
    tipo = request.GET.get("tipo", "")
    if tipo in NotaFiscal.Tipo.values:
        notas = notas.filter(tipo_documento=tipo)
    else:
        tipo = ""

    zero = Decimal("0")
    kpis = notas.aggregate(
        qtd=Count("id"),
        total=Sum("valor_total"),
        media=Avg("valor_total"),
        icms=Sum("valor_icms"),
        icms_st=Sum("valor_icms_st"),
        ipi=Sum("valor_ipi"),
        iss=Sum("valor_iss"),
        retencoes=Sum("valor_pis") + Sum("valor_cofins") + Sum("valor_inss") + Sum("valor_ir") + Sum("valor_csll")
        + Sum("valor_outras_retencoes"),
        qtd_servico=Count("id", filter=Q(tipo_documento=NotaFiscal.Tipo.NFSE)),
        total_servico=Sum("valor_total", filter=Q(tipo_documento=NotaFiscal.Tipo.NFSE)),
        frete=Sum("valor_frete"),
        produtos=Sum("valor_produtos"),
        emitentes=Count("emitente", distinct=True),
    )
    kpis = {k: (v if v is not None else zero) for k, v in kpis.items()}
    kpis["impostos"] = kpis["icms"] + kpis["icms_st"] + kpis["ipi"] + kpis["iss"] + kpis["retencoes"]
    kpis["qtd_produto"] = kpis["qtd"] - kpis["qtd_servico"]
    kpis["total_produto"] = kpis["total"] - kpis["total_servico"]
    kpis["carga"] = (kpis["impostos"] / kpis["total"] * 100) if kpis["total"] else zero

    por_mes = (
        notas.exclude(data_emissao=None)
        .annotate(mes=TruncMonth("data_emissao"))
        .values("mes")
        .annotate(qtd=Count("id"), total=Sum("valor_total"))
        .order_by("mes")
    )
    por_emitente = (
        notas.values("emitente__razao_social").annotate(qtd=Count("id"), total=Sum("valor_total")).order_by("-total")[:8]
    )
    por_uf = notas.values("emitente__uf").annotate(qtd=Count("id"), total=Sum("valor_total")).order_by("-total")
    maiores = notas.select_related("emitente").order_by("-valor_total")[:5]

    graficos = {
        "meses": {
            "rotulos": [f"{MESES[m['mes'].month - 1]}/{m['mes']:%y}" for m in por_mes],
            "total": [float(m["total"] or 0) for m in por_mes],
            "qtd": [m["qtd"] for m in por_mes],
        },
        "emitentes": {
            "rotulos": [e["emitente__razao_social"] or "Sem nome" for e in por_emitente],
            "total": [float(e["total"] or 0) for e in por_emitente],
        },
        "ufs": {
            "rotulos": [u["emitente__uf"] or "?" for u in por_uf],
            "total": [float(u["total"] or 0) for u in por_uf],
            "qtd": [u["qtd"] for u in por_uf],
        },
        "impostos": {
            "rotulos": ["ICMS", "ICMS ST", "IPI", "ISS", "Retenções federais"],
            "total": [float(kpis[c]) for c in ("icms", "icms_st", "ipi", "iss", "retencoes")],
        },
    }
    return render(
        request,
        "notas/estatisticas.html",
        {
            "kpis": kpis,
            "graficos": graficos,
            "maiores": maiores,
            "de": request.GET.get("de", "") if de else "",
            "ate": request.GET.get("ate", "") if ate else "",
            "tipo": tipo,
            "tipo_opcoes": NotaFiscal.Tipo.choices,
        },
    )


@admin_required
def importacao(request):
    return render(
        request,
        "notas/importacao.html",
        {
            "pasta": settings.DANFE_PASTA,
            "pasta_existe": Path(settings.DANFE_PASTA).is_dir(),
            "intervalo": settings.DANFE_MONITOR_INTERVALO,
            "sincronizacoes": Sincronizacao.objects.all()[:20],
            "problemas": NotaFiscal.objects.exclude(status=NotaFiscal.Status.OK).order_by("-importado_em")[:50],
            "total_importadas": NotaFiscal.objects.exclude(status=NotaFiscal.Status.ERRO).count(),
        },
    )
