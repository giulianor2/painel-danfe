"""Gera DANFEs FICTÍCIOS (layout padrão retrato) para testar o sistema.

Empresas, CNPJs, chaves e valores são inventados; servem apenas para demonstração.
"""
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

CODIGO_UF = {"MG": "31", "SP": "35", "RJ": "33", "PR": "41", "GO": "52", "ES": "32"}

EMITENTES = [
    ("Ferragens Candidés Ltda", "MG", "Divinópolis", "Av. Primeiro de Junho, 1420 - Centro", "35500002", "(37) 3221-4410"),
    ("Distribuidora Oeste Mineiro S.A.", "MG", "Itaúna", "Rua Silva Jardim, 87 - Centro", "35680054", "(37) 3241-9000"),
    ("Paulista Componentes Eletrônicos Ltda", "SP", "Campinas", "Rua Barão de Jaguara, 901 - Centro", "13015001", "(19) 3731-2200"),
    ("Papelaria e Informática Gutierrez ME", "MG", "Belo Horizonte", "Rua Curitiba, 545 - Centro", "30170120", "(31) 3270-1188"),
    ("Sul Fluminense Embalagens Ltda", "RJ", "Volta Redonda", "Av. Amaral Peixoto, 300 - Centro", "27253220", "(24) 3340-7711"),
    ("Agro Cerrado Insumos Ltda", "GO", "Rio Verde", "Rua Costa Gomes, 1200 - Centro", "75901010", "(64) 3621-5050"),
]
DESTINATARIOS = [
    ("Comercial Rio Itapecerica Ltda", "Divinópolis", "MG"),
    ("Mercearia Bom Pastor ME", "Divinópolis", "MG"),
    ("Oficina Mecânica Niterói Ltda", "Divinópolis", "MG"),
    ("Instituto Educacional Vale do Pará", "Nova Serrana", "MG"),
]
NATUREZAS = ["VENDA DE MERCADORIA", "VENDA DE PRODUÇÃO DO ESTABELECIMENTO", "REMESSA PARA CONSERTO", "VENDA A PRAZO"]
PRESTADORES = [
    ("Clínica Bom Viver Serviços Médicos Ltda", "Divinópolis", "MG", "3122306", "Rua Minas Gerais, 310, Sala 402, Centro", "35500007", "(37) 3222-1010", "04.01.01 - Medicina.", "Consultas médicas prestadas"),
    ("Sete Lagoas Tecnologia e Suporte Ltda", "Divinópolis", "MG", "3122306", "Av. Sete de Setembro, 955, Centro", "35500011", "(37) 3214-8080", "01.07.01 - Suporte técnico em informática.", "Suporte técnico e manutenção de computadores"),
    ("Contábil Itapecerica S/S", "Divinópolis", "MG", "3122306", "Rua Pernambuco, 120, Centro", "35500008", "(37) 3221-3030", "17.19.01 - Contabilidade.", "Honorários contábeis do mês"),
]
PRODUTOS = [
    "PARAFUSO SEXTAVADO 1/4 X 2", "CABO FLEXIVEL 2,5MM ROLO 100M", "RESMA PAPEL A4 75G", "CAIXA PAPELAO 40X30X30",
    "RESISTOR 10K 1/4W (CENTO)", "DISJUNTOR BIPOLAR 32A", "TONER COMPATIVEL 85A", "FERTILIZANTE NPK 20-05-20 50KG",
    "FITA ADESIVA 48MM X 100M", "ROLAMENTO 6204 ZZ",
]


def _dv_cnpj(base):
    def dv(nums, pesos):
        resto = sum(int(n) * p for n, p in zip(nums, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = dv(base + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return base + d1 + d2


def _dv_chave(chave43):
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    resto = sum(int(d) * pesos[i % 8] for i, d in enumerate(reversed(chave43))) % 11
    return "0" if resto in (0, 1) else str(11 - resto)


def br(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_cnpj(v):
    return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"


class Command(BaseCommand):
    help = "Gera PDFs de DANFE fictícios na pasta de notas."

    def add_arguments(self, parser):
        parser.add_argument("--quantidade", type=int, default=14, help="DANFEs de produto (NF-e)")
        parser.add_argument("--servico", type=int, default=5, help="Notas de serviço (DANFSe padrão nacional)")
        parser.add_argument("--pasta", help="Destino (padrão: DANFE_PASTA)")
        parser.add_argument("--semente", type=int, default=2026)

    def handle(self, *args, **op):
        pasta = Path(op["pasta"] or settings.DANFE_PASTA)
        pasta.mkdir(parents=True, exist_ok=True)
        rnd = random.Random(op["semente"])
        emitentes = []
        for i, e in enumerate(EMITENTES):
            cnpj = _dv_cnpj(f"{rnd.randint(10, 98):02d}{rnd.randint(100, 999)}{rnd.randint(100, 999)}0001")
            ie = f"{rnd.randint(10**11, 10**12 - 1)}"
            emitentes.append((*e, cnpj, ie, 1000 + rnd.randint(0, 800)))
        hoje = date.today()
        for n in range(op["quantidade"]):
            idx = rnd.choices(range(len(emitentes)), weights=[5, 4, 3, 3, 2, 1])[0]
            nome, uf, cidade, endereco, cep, fone, cnpj, ie, base_num = emitentes[idx]
            numero = base_num + n * 7 + rnd.randint(1, 5)
            emissao = hoje - timedelta(days=rnd.randint(1, 170))
            itens = []
            for _ in range(rnd.randint(2, 5)):
                qtd = rnd.randint(1, 40)
                unit = Decimal(rnd.randint(350, 42000)) / 100
                itens.append((rnd.choice(PRODUTOS), qtd, unit, (unit * qtd).quantize(Decimal("0.01"))))
            produtos = sum(i[3] for i in itens)
            aliquota = Decimal("0.18") if uf == "MG" else Decimal("0.12")
            icms = (produtos * aliquota).quantize(Decimal("0.01"))
            tem_st = rnd.random() < 0.3
            base_st = (produtos * Decimal("1.4")).quantize(Decimal("0.01")) if tem_st else Decimal("0")
            st = (base_st * Decimal("0.18") - icms).quantize(Decimal("0.01")) if tem_st else Decimal("0")
            ipi = (produtos * Decimal("0.05")).quantize(Decimal("0.01")) if rnd.random() < 0.4 else Decimal("0")
            frete = Decimal(rnd.choice([0, 0, 45, 80, 120, 260]))
            desconto = (produtos * Decimal("0.03")).quantize(Decimal("0.01")) if rnd.random() < 0.25 else Decimal("0")
            total = produtos + st + ipi + frete - desconto
            chave43 = (
                f"{CODIGO_UF[uf]}{emissao:%y%m}{cnpj}55001{numero:09d}1{rnd.randint(10**7, 10**8 - 1)}"
            )
            chave = chave43 + _dv_chave(chave43)
            dest = rnd.choice(DESTINATARIOS)
            nota = dict(
                emit_nome=nome.upper(), emit_endereco=endereco, emit_cidade=cidade, emit_uf=uf, emit_cep=cep,
                emit_fone=fone, emit_cnpj=cnpj, emit_ie=ie, numero=numero, serie=1, emissao=emissao,
                natureza=rnd.choice(NATUREZAS), chave=chave,
                protocolo=f"1{CODIGO_UF[uf]}{emissao:%y}{rnd.randint(10**9, 10**10 - 1)} - {emissao:%d/%m/%Y} {rnd.randint(8, 17):02d}:{rnd.randint(0, 59):02d}:{rnd.randint(0, 59):02d}",
                dest_nome=dest[0].upper(), dest_cidade=dest[1], dest_uf=dest[2],
                dest_cnpj=_dv_cnpj(f"{rnd.randint(10, 98):02d}{rnd.randint(100, 999)}{rnd.randint(100, 999)}0001"),
                itens=itens, base_icms=produtos, icms=icms, base_st=base_st, st=st, produtos=produtos,
                frete=frete, seguro=Decimal("0"), desconto=desconto, outras=Decimal("0"), ipi=ipi, total=total,
                aliquota=aliquota,
            )
            arquivo = pasta / f"NFe_{numero:09d}_{cnpj}.pdf"
            desenhar_danfe(arquivo, nota)
        prestadores = [
            (*p, _dv_cnpj(f"{rnd.randint(10, 98):02d}{rnd.randint(100, 999)}{rnd.randint(100, 999)}0001"), str(rnd.randint(10000, 99999)))
            for p in PRESTADORES
        ]
        for n in range(op["servico"]):
            nome, cidade, uf, cod_mun, endereco, cep, fone, cod_servico, descricao, cnpj, im = prestadores[n % len(prestadores)]
            numero = 40 + n * 13 + rnd.randint(1, 9)
            emissao = hoje - timedelta(days=rnd.randint(1, 170))
            valor = Decimal(rnd.randint(18000, 320000)) / 100
            tributa = rnd.random() < 0.6
            aliquota = Decimal(rnd.choice(["2.00", "3.00", "5.00"])) if tributa else Decimal("0")
            iss = (valor * aliquota / 100).quantize(Decimal("0.01"))
            irrf = (valor * Decimal("0.015")).quantize(Decimal("0.01")) if rnd.random() < 0.3 else Decimal("0")
            chave49 = f"{cod_mun}22{cnpj}{numero:013d}{emissao:%y%m}{rnd.randint(10**8, 10**9 - 1)}"
            dest = rnd.choice(DESTINATARIOS)
            nota = dict(
                chave=chave49 + _dv_chave(chave49), numero=numero, emissao=emissao, hora=f"{rnd.randint(8, 17):02d}:{rnd.randint(0, 59):02d}:{rnd.randint(0, 59):02d}",
                prest_nome=nome.upper(), prest_cnpj=cnpj, prest_im=im, prest_fone=fone, prest_endereco=endereco,
                prest_cidade=f"{cidade} - {uf}", prest_cep=cep, cod_servico=cod_servico, descricao=descricao,
                tom_nome=dest[0].upper(), tom_cidade=f"{dest[1]} - {dest[2]}",
                tom_cnpj=_dv_cnpj(f"{rnd.randint(10, 98):02d}{rnd.randint(100, 999)}{rnd.randint(100, 999)}0001"),
                valor=valor, base=valor if tributa else None, aliquota=aliquota if tributa else None, iss=iss if tributa else None,
                irrf=irrf or None, liquido=valor - irrf,
            )
            desenhar_danfse(pasta / f"NFSe_{numero:06d}_{cnpj}.pdf", nota)
        self.stdout.write(
            self.style.SUCCESS(f"{op['quantidade']} DANFE(s) e {op['servico']} nota(s) de serviço fictício(s) gerado(s) em {pasta}")
        )


def desenhar_danfe(arquivo, n):
    from reportlab.graphics.barcode import code128
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(arquivo), pagesize=A4)
    c.setTitle(f"DANFE {n['numero']} (fictício)")
    LARG, ALT = A4
    x0, larg = 8 * mm, LARG - 16 * mm
    c.setLineWidth(0.5)

    def caixa(x, y, w, h, rotulo="", valor="", direita=False, tamanho=9, negrito=False):
        """Caixa com rótulo pequeno em cima e valor embaixo. y = topo da caixa."""
        c.rect(x, y - h, w, h)
        if rotulo:
            c.setFont("Helvetica", 5)
            c.drawString(x + 1.5, y - 6.5, rotulo)
        if valor != "":
            c.setFont("Helvetica-Bold" if negrito else "Helvetica", tamanho)
            if direita:
                c.drawRightString(x + w - 2.5, y - h + 3.5, str(valor))
            else:
                c.drawString(x + 2.5, y - h + 3.5, str(valor))

    def linha(y, h, celulas):
        """celulas: (fração da largura, rótulo, valor, direita?)"""
        x = x0
        for fracao, rotulo, valor, *resto in celulas:
            w = larg * fracao
            caixa(x, y, w, h, rotulo, valor, direita=bool(resto and resto[0]))
            x += w
        return y - h

    def titulo(y, texto):
        c.setFont("Helvetica-Bold", 6)
        c.drawString(x0, y - 8, texto)
        return y - 10

    numero_fmt = f"{n['numero']:09d}"
    numero_fmt = f"{numero_fmt[:3]}.{numero_fmt[3:6]}.{numero_fmt[6:]}"
    y = ALT - 8 * mm

    # Canhoto
    c.rect(x0, y - 22, larg * 0.82, 22)
    c.setFont("Helvetica", 5.5)
    c.drawString(x0 + 2, y - 8, f"RECEBEMOS DE {n['emit_nome']} OS PRODUTOS E/OU SERVIÇOS CONSTANTES DA NOTA FISCAL INDICADA AO LADO")
    c.setFont("Helvetica", 5)
    c.drawString(x0 + 2, y - 19, "DATA DE RECEBIMENTO")
    c.drawString(x0 + 110, y - 19, "IDENTIFICAÇÃO E ASSINATURA DO RECEBEDOR")
    c.rect(x0 + larg * 0.82, y - 22, larg * 0.18, 22)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x0 + larg * 0.91, y - 9, "NF-e")
    c.setFont("Helvetica", 7)
    c.drawCentredString(x0 + larg * 0.91, y - 18, f"Nº {numero_fmt}  SÉRIE {n['serie']:03d}")
    y -= 22
    c.setDash(2, 2)
    c.line(x0, y - 4, x0 + larg, y - 4)
    c.setDash()
    y -= 8

    # Cabeçalho: emitente | DANFE | código de barras
    h = 92
    w1, w2 = larg * 0.40, larg * 0.16
    w3 = larg - w1 - w2
    c.rect(x0, y - h, w1, h)
    c.setFont("Helvetica", 5)
    c.drawString(x0 + 1.5, y - 6.5, "IDENTIFICAÇÃO DO EMITENTE")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0 + 4, y - 30, n["emit_nome"])
    c.setFont("Helvetica", 8)
    c.drawString(x0 + 4, y - 46, n["emit_endereco"])
    c.drawString(x0 + 4, y - 57, f"{n['emit_cidade']} - {n['emit_uf']}  CEP: {n['emit_cep'][:5]}-{n['emit_cep'][5:]}")
    c.drawString(x0 + 4, y - 68, f"Fone: {n['emit_fone']}")

    xd = x0 + w1
    c.rect(xd, y - h, w2, h)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(xd + w2 / 2, y - 15, "DANFE")
    c.setFont("Helvetica", 5.5)
    for i, t in enumerate(["Documento Auxiliar da", "Nota Fiscal Eletrônica"]):
        c.drawCentredString(xd + w2 / 2, y - 24 - i * 6.5, t)
    c.setFont("Helvetica", 7)
    c.drawString(xd + 6, y - 43, "0 - ENTRADA")
    c.drawString(xd + 6, y - 53, "1 - SAÍDA")
    c.rect(xd + w2 - 22, y - 56, 13, 14)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(xd + w2 - 18.5, y - 53, "1")
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(xd + w2 / 2, y - 68, f"Nº {numero_fmt}")
    c.drawCentredString(xd + w2 / 2, y - 78, f"SÉRIE {n['serie']:03d}")
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(xd + w2 / 2, y - 87, "FOLHA 1/1")

    xb = xd + w2
    c.rect(xb, y - h, w3, h)
    barras = code128.Code128(n["chave"], barHeight=30, barWidth=0.62, quiet=False)
    barras.drawOn(c, xb + (w3 - barras.width) / 2, y - 36)
    c.line(xb, y - 42, xb + w3, y - 42)
    c.setFont("Helvetica", 5)
    c.drawString(xb + 1.5, y - 48.5, "CHAVE DE ACESSO")
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(xb + w3 / 2, y - 60, " ".join(n["chave"][i : i + 4] for i in range(0, 44, 4)))
    c.line(xb, y - 65, xb + w3, y - 65)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(xb + w3 / 2, y - 75, "Consulta de autenticidade no portal nacional da NF-e")
    c.drawCentredString(xb + w3 / 2, y - 84, "www.nfe.fazenda.gov.br/portal ou no site da Sefaz Autorizadora")
    y -= h

    y = linha(y, 22, [(0.56, "NATUREZA DA OPERAÇÃO", n["natureza"]), (0.44, "PROTOCOLO DE AUTORIZAÇÃO DE USO", n["protocolo"])])
    y = linha(y, 22, [
        (0.34, "INSCRIÇÃO ESTADUAL", n["emit_ie"]),
        (0.33, "INSCRIÇÃO ESTADUAL DO SUBST. TRIBUT.", ""),
        (0.33, "CNPJ", fmt_cnpj(n["emit_cnpj"])),
    ])

    y = titulo(y, "DESTINATÁRIO / REMETENTE")
    y = linha(y, 22, [
        (0.60, "NOME / RAZÃO SOCIAL", n["dest_nome"]),
        (0.24, "CNPJ / CPF", fmt_cnpj(n["dest_cnpj"])),
        (0.16, "DATA DA EMISSÃO", f"{n['emissao']:%d/%m/%Y}"),
    ])
    y = linha(y, 22, [
        (0.48, "ENDEREÇO", "RUA GOIÁS, 1000"),
        (0.24, "BAIRRO / DISTRITO", "CENTRO"),
        (0.12, "CEP", "35500-001"),
        (0.16, "DATA DA SAÍDA/ENTRADA", f"{n['emissao'] + timedelta(days=1):%d/%m/%Y}"),
    ])
    y = linha(y, 22, [
        (0.40, "MUNICÍPIO", n["dest_cidade"].upper()),
        (0.06, "UF", n["dest_uf"]),
        (0.18, "FONE / FAX", "(37) 3000-0000"),
        (0.20, "INSCRIÇÃO ESTADUAL", "ISENTO"),
        (0.16, "HORA DA SAÍDA", "10:00:00"),
    ])

    y = titulo(y, "CÁLCULO DO IMPOSTO")
    y = linha(y, 22, [
        (0.20, "BASE DE CÁLCULO DO ICMS", br(n["base_icms"]), True),
        (0.18, "VALOR DO ICMS", br(n["icms"]), True),
        (0.22, "BASE DE CÁLCULO DO ICMS ST", br(n["base_st"]), True),
        (0.18, "VALOR DO ICMS ST", br(n["st"]), True),
        (0.22, "VALOR TOTAL DOS PRODUTOS", br(n["produtos"]), True),
    ])
    y = linha(y, 22, [
        (0.15, "VALOR DO FRETE", br(n["frete"]), True),
        (0.15, "VALOR DO SEGURO", br(n["seguro"]), True),
        (0.14, "DESCONTO", br(n["desconto"]), True),
        (0.20, "OUTRAS DESPESAS ACESSÓRIAS", br(n["outras"]), True),
        (0.14, "VALOR DO IPI", br(n["ipi"]), True),
        (0.22, "VALOR TOTAL DA NOTA", br(n["total"]), True),
    ])

    y = titulo(y, "TRANSPORTADOR / VOLUMES TRANSPORTADOS")
    y = linha(y, 22, [
        (0.40, "RAZÃO SOCIAL", "TRANSPORTES FICTÍCIOS LTDA"),
        (0.18, "FRETE POR CONTA", "0 - EMITENTE" if n["frete"] else "9 - SEM FRETE"),
        (0.12, "CÓDIGO ANTT", ""),
        (0.10, "PLACA DO VEÍCULO", "ABC1D23"),
        (0.20, "CNPJ/CPF", "00.000.000/0001-91"),
    ])

    y = titulo(y, "DADOS DOS PRODUTOS / SERVIÇOS")
    colunas = [(0.08, "CÓDIGO"), (0.36, "DESCRIÇÃO DO PRODUTO / SERVIÇO"), (0.08, "NCM/SH"), (0.06, "CFOP"), (0.05, "UN"),
               (0.07, "QTD."), (0.10, "V. UNITÁRIO"), (0.10, "V. TOTAL"), (0.10, "ALÍQ. ICMS")]
    x = x0
    for fracao, rotulo in colunas:
        c.rect(x, y - 12, larg * fracao, 12)
        c.setFont("Helvetica", 5)
        c.drawString(x + 1.5, y - 8, rotulo)
        x += larg * fracao
    y -= 12
    altura_itens = 170
    c.rect(x0, y - altura_itens, larg, altura_itens)
    c.setFont("Helvetica", 7)
    yi = y - 10
    for i, (desc, qtd, unit, tot) in enumerate(n["itens"], 1):
        valores = [f"{i:04d}", desc, "73181500", "5102", "UN", str(qtd), br(unit), br(tot), f"{n['aliquota'] * 100:.0f}%"]
        x = x0
        for (fracao, _), valor in zip(colunas, valores):
            c.drawString(x + 1.5, yi, valor)
            x += larg * fracao
        yi -= 10
    y -= altura_itens

    y = titulo(y, "DADOS ADICIONAIS")
    c.rect(x0, y - 60, larg, 60)
    c.setFont("Helvetica", 5)
    c.drawString(x0 + 1.5, y - 6.5, "INFORMAÇÕES COMPLEMENTARES")
    c.setFont("Helvetica", 7)
    c.drawString(x0 + 3, y - 18, "DOCUMENTO FICTÍCIO, SEM VALOR FISCAL - gerado apenas para demonstração do Painel DANFE.")
    c.showPage()
    c.save()


def desenhar_danfse(arquivo, n):
    """DANFSe fictício no desenho do padrão nacional (rótulo em cima, valor embaixo, 4 colunas)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(arquivo), pagesize=A4)
    c.setTitle(f"DANFSe {n['numero']} (fictício)")
    LARG, ALT = A4
    COL = [14, 156, 298, 439]
    estado = {"y": ALT - 22}

    def rs(valor):
        return "-" if valor is None else f"R$ {br(valor)}"

    def secao(texto, colunas=()):
        estado["y"] -= 6
        c.setLineWidth(0.4)
        c.line(14, estado["y"] + 9, LARG - 14, estado["y"] + 9)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(COL[0], estado["y"], texto)
        return estado["y"]

    def campos(*celulas, rotulos_na_secao=False):
        """celulas: (coluna, rótulo, valor)."""
        y = estado["y"] if rotulos_na_secao else estado["y"] - 13
        for col, rotulo, valor in celulas:
            c.setFont("Helvetica", 7)
            c.drawString(COL[col], y, rotulo)
            c.setFont("Helvetica", 8)
            c.drawString(COL[col], y - 9, str(valor))
        estado["y"] = y - 9

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(250, estado["y"], "DANFSe v1.0")
    c.setFont("Helvetica", 9)
    c.drawCentredString(250, estado["y"] - 10, "Documento Auxiliar da NFS-e")
    c.setFont("Helvetica", 8)
    c.drawString(COL[3], estado["y"] + 4, "Prefeitura Municipal (fictícia)")
    c.setFont("Helvetica", 6)
    c.drawString(COL[3], estado["y"] - 5, "Secretaria Municipal de Fazenda")
    estado["y"] -= 18
    campos((0, "Chave de Acesso da NFS-e", n["chave"]))
    campos(
        (0, "Número da NFS-e", n["numero"]),
        (1, "Competência da NFS-e", f"{n['emissao']:%d/%m/%Y}"),
        (2, "Data e Hora da emissão da NFS-e", f"{n['emissao']:%d/%m/%Y} {n['hora']}"),
    )
    campos(
        (0, "Número da DPS", n["numero"] - 10),
        (1, "Série da DPS", "70000"),
        (2, "Data e Hora da emissão da DPS", f"{n['emissao']:%d/%m/%Y} {n['hora']}"),
    )
    estado["y"] -= 12
    secao("EMITENTE DA NFS-e")
    campos((1, "CNPJ / CPF / NIF", fmt_cnpj(n["prest_cnpj"])), (2, "Inscrição Municipal", n["prest_im"]),
           (3, "Telefone", n["prest_fone"]), rotulos_na_secao=True)
    c.drawString(COL[0], estado["y"], "Prestador do Serviço")
    campos((0, "Nome / Nome Empresarial", n["prest_nome"]), (2, "E-mail", "-"))
    campos((0, "Endereço", n["prest_endereco"]), (2, "Município", n["prest_cidade"]),
           (3, "CEP", f"{n['prest_cep'][:5]}-{n['prest_cep'][5:]}"))
    estado["y"] -= 12
    secao("TOMADOR DO SERVIÇO")
    campos((1, "CNPJ / CPF / NIF", fmt_cnpj(n["tom_cnpj"])), (2, "Inscrição Municipal", "-"), (3, "Telefone", "-"),
           rotulos_na_secao=True)
    campos((0, "Nome / Nome Empresarial", n["tom_nome"]), (2, "E-mail", "-"))
    campos((0, "Endereço", "RUA GOIÁS, 1000, CENTRO"), (2, "Município", n["tom_cidade"]), (3, "CEP", "35500-001"))
    estado["y"] -= 12
    secao("SERVIÇO PRESTADO")
    campos((0, "Código de Tributação Nacional", n["cod_servico"]), (2, "Local da Prestação", n["prest_cidade"]),
           (3, "País da Prestação", "-"))
    campos((0, "Descrição do Serviço", n["descricao"]))
    estado["y"] -= 12
    secao("TRIBUTAÇÃO MUNICIPAL")
    campos((0, "Tributação do ISSQN", "Operação Tributável"), (2, "Município de Incidência do ISSQN", n["prest_cidade"]))
    campos((0, "Valor do Serviço", rs(n["valor"])), (1, "Desconto Incondicionado", "-"),
           (2, "Total Deduções/Reduções", "-"), (3, "Cálculo do BM", "-"))
    campos((0, "BC ISSQN", rs(n["base"])), (1, "Alíquota Aplicada", "-" if n["aliquota"] is None else f"{br(n['aliquota'])}%"),
           (2, "Retenção do ISSQN", "Não Retido"), (3, "ISSQN Apurado", rs(n["iss"])))
    estado["y"] -= 12
    secao("TRIBUTAÇÃO FEDERAL")
    campos((0, "IRRF", rs(n["irrf"])), (1, "Contribuição Previdenciária - Retida", "-"),
           (2, "Contribuições Sociais - Retidas", "-"))
    estado["y"] -= 12
    secao("VALOR TOTAL DA NFS-E")
    campos((0, "Valor do Serviço", rs(n["valor"])), (1, "Desconto Condicionado", "-"),
           (2, "Desconto Incondicionado", "-"), (3, "ISSQN Retido", "-"))
    campos((0, "Total das Retenções Federais", rs(n["irrf"])), (3, "Valor Líquido da NFS-e", rs(n["liquido"])))
    estado["y"] -= 12
    secao("INFORMAÇÕES COMPLEMENTARES")
    c.setFont("Helvetica", 8)
    c.drawString(COL[0], estado["y"] - 12, "DOCUMENTO FICTÍCIO, SEM VALOR FISCAL - gerado apenas para demonstração do Painel DANFE.")
    c.showPage()
    c.save()
