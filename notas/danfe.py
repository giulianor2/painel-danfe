"""Leitura de DANFE (PDF com texto) usando pdfplumber.

Estratégia
----------
1. A chave de acesso (44 dígitos) é localizada e validada pelo dígito verificador.
   Dela saem, de forma confiável: UF, CNPJ do emitente, modelo, série e número.
2. Os demais campos são lidos pela posição: o DANFE é uma grade de caixas com um
   rótulo pequeno em cima e o valor logo abaixo. Para cada rótulo conhecido,
   pegamos o texto imediatamente abaixo, dentro da largura da caixa.
3. Para os valores do bloco "CÁLCULO DO IMPOSTO" há um plano B por ordem das colunas.

PDFs digitalizados (imagem, sem texto) não são lidos: seria necessário OCR.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

RE_DINHEIRO = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$|^\d+,\d{2}$")
RE_DATA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


class DanfeErro(Exception):
    """O arquivo não pôde ser interpretado como DANFE."""


@dataclass
class DadosDanfe:
    tipo_documento: str = "NFE"  # "NFE" (produto) ou "NFSE" (serviço)
    extras: dict = field(default_factory=dict)  # campos próprios da nota de serviço
    emit_im: str = ""
    chave_acesso: str = ""
    numero: int | None = None
    serie: int | None = None
    modelo: str = ""
    tipo_operacao: str = ""
    natureza_operacao: str = ""
    protocolo: str = ""
    data_emissao: date | None = None
    data_saida: date | None = None
    emit_cnpj: str = ""
    emit_nome: str = ""
    emit_ie: str = ""
    emit_endereco: str = ""
    emit_municipio: str = ""
    emit_uf: str = ""
    emit_cep: str = ""
    emit_telefone: str = ""
    dest_nome: str = ""
    dest_documento: str = ""
    dest_municipio: str = ""
    dest_uf: str = ""
    valores: dict = field(default_factory=dict)
    pendencias: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Utilitários
# --------------------------------------------------------------------------
def _norm(texto: str) -> str:
    """Maiúsculas, sem acentos e só letras/dígitos (para comparar rótulos)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", sem_acento.upper())


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def chave_valida(chave: str, tamanho: int = 44) -> bool:
    """Confere o dígito verificador (módulo 11) da chave de acesso.

    NF-e: 44 dígitos. NFS-e padrão nacional: 50 dígitos (mesmo cálculo).
    """
    if len(chave) != tamanho or not chave.isdigit():
        return False
    pesos = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = sum(int(d) * pesos[i % 8] for i, d in enumerate(reversed(chave[:-1])))
    resto = soma % 11
    dv = 0 if resto in (0, 1) else 11 - resto
    return dv == int(chave[-1])


def _dinheiro(texto: str) -> Decimal | None:
    texto = (texto or "").replace("R$", "").strip()
    achado = re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}", texto)
    if not achado:
        return None
    try:
        return Decimal(achado.group().replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _data(texto: str) -> date | None:
    achado = RE_DATA.search(texto or "")
    if not achado:
        return None
    try:
        return datetime.strptime(achado.group(), "%d/%m/%Y").date()
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Leitura posicional
# --------------------------------------------------------------------------
class Pagina:
    def __init__(self, page, x_tolerance: float = 1.5):
        self.largura = float(page.width)
        self.palavras = page.extract_words(x_tolerance=x_tolerance, y_tolerance=2, extra_attrs=["size"])
        self.linhas = self._agrupar_linhas(self.palavras)
        self.texto = page.extract_text(x_tolerance=x_tolerance) or ""

    @staticmethod
    def _agrupar_linhas(palavras):
        linhas = []
        for p in sorted(palavras, key=lambda w: (w["top"], w["x0"])):
            if linhas and abs(linhas[-1][0]["top"] - p["top"]) <= 2.5:
                linhas[-1].append(p)
            else:
                linhas.append([p])
        for linha in linhas:
            linha.sort(key=lambda w: w["x0"])
        return linhas

    def achar_rotulo(self, rotulo: str, ocorrencia: int = 0):
        """Localiza o rótulo e devolve a "caixa" (x0, x1, top, bottom, tamanho da fonte)."""
        alvo = _norm(rotulo)
        achados = []
        for linha in self.linhas:
            for i in range(len(linha)):
                junto = ""
                for j in range(i, len(linha)):
                    junto += _norm(linha[j]["text"])
                    if not alvo.startswith(junto):
                        break
                    if junto == alvo:
                        proxima = linha[j + 1] if j + 1 < len(linha) else None
                        # Se a próxima palavra está "colada", o rótulo é maior que o procurado
                        # (ex.: "VALOR DO ICMS" dentro de "VALOR DO ICMS ST").
                        if proxima is not None and proxima["x0"] - linha[j]["x1"] < 5:
                            break
                        achados.append(
                            {
                                "x0": linha[i]["x0"],
                                "x1": proxima["x0"] if proxima is not None else self.largura,
                                "top": linha[i]["top"],
                                "bottom": max(w["bottom"] for w in linha[i : j + 1]),
                                "size": linha[i].get("size") or 0,
                            }
                        )
                        break
        achados.sort(key=lambda c: (c["top"], c["x0"]))
        return achados[ocorrencia] if len(achados) > ocorrencia else None

    def valor_abaixo(self, rotulos, ocorrencia: int = 0, alcance: float = 16, fonte_maior: bool = True,
                     multilinha: bool = False) -> str:
        """Texto logo abaixo de um dos rótulos, dentro da caixa.

        fonte_maior: exige que o valor tenha fonte maior que a do rótulo (evita pegar o rótulo
        da linha de baixo quando o campo está vazio). multilinha: junta as linhas seguidas.
        """
        for rotulo in rotulos:
            caixa = self.achar_rotulo(rotulo, ocorrencia)
            if not caixa:
                continue
            candidatas = [
                w
                for w in self.palavras
                if caixa["bottom"] - 1 <= w["top"] <= caixa["bottom"] + (alcance if not multilinha else 90)
                and caixa["x0"] - 3 <= w["x0"] < caixa["x1"] - 1
                and (not fonte_maior or not caixa["size"] or not w.get("size") or w["size"] > caixa["size"] + 0.4)
            ]
            candidatas = [w for w in candidatas if w["top"] > caixa["top"] + 2]
            if not candidatas:
                return ""
            tops = sorted({round(w["top"], 1) for w in candidatas})
            if tops[0] > caixa["bottom"] + alcance:
                return ""
            usados = [tops[0]]
            if multilinha:
                for t in tops[1:]:
                    if t - usados[-1] > 11:
                        break
                    usados.append(t)
            linhas = []
            for t in usados:
                linha = sorted((w for w in candidatas if abs(w["top"] - t) <= 0.6), key=lambda w: w["x0"])
                linhas.append(" ".join(w["text"] for w in linha))
            return " ".join(linhas).strip()
        return ""


ROTULOS_VALORES = {
    "base_icms": ["BASE DE CÁLCULO DO ICMS", "BASE DE CÁLC. DO ICMS", "BASE DE CÁLC. ICMS", "BASE CÁLC. ICMS"],
    "valor_icms": ["VALOR DO ICMS", "VALOR ICMS"],
    "base_icms_st": [
        "BASE DE CÁLCULO DO ICMS ST", "BASE DE CÁLCULO DO ICMS SUBSTITUIÇÃO", "BASE DE CÁLC. ICMS S.T.",
        "BASE DE CÁLC. ICMS SUBST.", "BASE CÁLC. ICMS SUBST.", "BASE DE CÁLCULO ICMS ST",
    ],
    "valor_icms_st": ["VALOR DO ICMS ST", "VALOR DO ICMS SUBSTITUIÇÃO", "VALOR DO ICMS SUBST.", "VALOR ICMS SUBST.", "VALOR ICMS ST"],
    "valor_produtos": ["VALOR TOTAL DOS PRODUTOS", "V. TOTAL PRODUTOS", "VALOR TOTAL PRODUTOS", "V. TOTAL DOS PRODUTOS"],
    "valor_frete": ["VALOR DO FRETE", "VALOR FRETE"],
    "valor_seguro": ["VALOR DO SEGURO", "VALOR SEGURO"],
    "valor_desconto": ["DESCONTO", "VALOR DO DESCONTO"],
    "valor_outras": ["OUTRAS DESPESAS ACESSÓRIAS", "OUTRAS DESP. ACESSÓRIAS", "OUTRAS DESPESAS", "OUTRAS DESP. ACESS."],
    "valor_ipi": ["VALOR TOTAL DO IPI", "VALOR DO IPI", "VALOR TOTAL IPI", "VALOR IPI"],
    "valor_total": ["VALOR TOTAL DA NOTA", "V. TOTAL DA NOTA", "VALOR TOTAL NOTA"],
}


def _valores_por_ordem(texto: str) -> dict:
    """Plano B: lê as duas linhas de números do bloco CÁLCULO DO IMPOSTO pela ordem."""
    linhas = texto.splitlines()
    inicio = next((i for i, l in enumerate(linhas) if "CALCULODOIMPOSTO" in _norm(l)), None)
    if inicio is None:
        return {}
    numericas = []
    for linha in linhas[inicio + 1 : inicio + 9]:
        partes = linha.split()
        if len(partes) >= 5 and all(RE_DINHEIRO.match(p) for p in partes):
            numericas.append([_dinheiro(p) for p in partes])
        if len(numericas) == 2:
            break
    if len(numericas) < 2:
        return {}
    l1, l2 = numericas
    return {
        "base_icms": l1[0], "valor_icms": l1[1], "base_icms_st": l1[2], "valor_icms_st": l1[3],
        "valor_produtos": l1[-1],
        "valor_frete": l2[0], "valor_seguro": l2[1], "valor_desconto": l2[2], "valor_outras": l2[3],
        "valor_ipi": l2[4], "valor_total": l2[-1],
    }


def _achar_chave(texto: str) -> str:
    # A chave costuma vir em 11 grupos de 4 dígitos; às vezes tudo junto.
    for achado in re.finditer(r"(?<!\d)(?:\d{4}[ \t]*){10}\d{4}(?!\d)", texto):
        chave = so_digitos(achado.group())
        if chave_valida(chave):
            return chave
    for achado in re.finditer(r"\d{44}", so_digitos(texto)):  # último recurso
        if chave_valida(achado.group()):
            return achado.group()
    return ""


def _emitente(pagina: Pagina, dados: DadosDanfe):
    """Bloco do emitente: canto superior esquerdo, acima de NATUREZA DA OPERAÇÃO."""
    achado = re.search(r"RECEBEMOS\s+DE\s+(.+?)\s+OS\s+PRODUTOS", pagina.texto, re.S | re.I)
    if achado:
        dados.emit_nome = " ".join(achado.group(1).split())

    natureza = pagina.achar_rotulo("NATUREZA DA OPERAÇÃO")
    if not natureza:
        return
    palavra_danfe = next(
        (w for w in pagina.palavras if _norm(w["text"]) == "DANFE" and w["top"] < natureza["top"]), None
    )
    limite_x = palavra_danfe["x0"] - 4 if palavra_danfe else pagina.largura * 0.42
    # A coluna central (DANFE / 0 - ENTRADA / 1 - SAÍDA) pode começar antes da palavra "DANFE".
    for linha in pagina.linhas:
        if not linha or linha[0]["top"] >= natureza["top"]:
            continue
        for i, w in enumerate(linha):
            if _norm(w["text"]) in ("ENTRADA", "SAIDA", "AUXILIAR"):
                inicio = i
                while inicio > 0 and linha[inicio]["x0"] - linha[inicio - 1]["x1"] < 6:
                    inicio -= 1
                if linha[inicio]["x0"] > pagina.largura * 0.2:
                    limite_x = min(limite_x, linha[inicio]["x0"] - 3)
    ident = pagina.achar_rotulo("IDENTIFICAÇÃO DO EMITENTE")
    topo = ident["bottom"] if ident else max(natureza["top"] - 120, 0)
    if not ident and palavra_danfe:
        topo = palavra_danfe["top"] - 6
    bloco = [
        linha_filtrada
        for linha in pagina.linhas
        if (linha_filtrada := [w for w in linha if w["x1"] <= limite_x and topo <= w["top"] < natureza["top"] - 2])
    ]
    if not bloco:
        return
    textos = [" ".join(w["text"] for w in linha) for linha in bloco]
    tamanhos = [max(w.get("size") or 0 for w in linha) for linha in bloco]
    maior = max(range(len(bloco)), key=lambda i: tamanhos[i])
    if not dados.emit_nome:
        dados.emit_nome = textos[maior]
    nome = _norm(dados.emit_nome)

    def eh_nome(i):
        t = _norm(textos[i])
        if t and (nome.startswith(t) or t.startswith(nome)):
            return True
        return i == maior and tamanhos[i] > min(tamanhos) + 0.5  # linha em destaque = razão social

    resto = [textos[i] for i in range(len(textos)) if not eh_nome(i)]
    completo = " ".join(resto)

    if cep := re.search(r"\b(\d{2}\.?\d{3}-?\d{3})\b", completo):
        dados.emit_cep = so_digitos(cep.group(1))
    if fone := re.search(r"\(?\d{2}\)?\s?\d{4,5}-?\d{4}", completo):
        dados.emit_telefone = fone.group().strip()

    limpas = []
    for linha in resto:
        if dados.emit_uf and not dados.emit_municipio:
            # "Divinópolis - MG", "DIVINOPOLIS/MG", "Centro - Divinópolis - MG"
            if mun := re.search(rf"([A-Za-zÀ-ÿ'\. ]{{3,}}?)\s*[-/]\s*{dados.emit_uf}\b", linha):
                dados.emit_municipio = mun.group(1).strip(" -,")
        linha = re.sub(r"(?i)\b(fone|tel|telefone)(/fax)?\b[:.]?.*$", "", linha)
        linha = re.sub(r"(?i)\bCEP\b[:.]?\s*\d{2}\.?\d{3}-?\d{3}", "", linha)
        linha = " ".join(linha.split()).strip(" -,")
        if linha:
            limpas.append(linha)
    dados.emit_endereco = ", ".join(limpas)[:300]


def ler_danfe(caminho: str | Path) -> DadosDanfe:
    """Lê um PDF de DANFE e devolve os dados. Levanta DanfeErro se não for possível."""
    try:
        with pdfplumber.open(str(caminho)) as pdf:
            if not pdf.pages:
                raise DanfeErro("PDF sem páginas.")
            pagina = Pagina(pdf.pages[0])
    except DanfeErro:
        raise
    except Exception as exc:  # PDF corrompido, protegido por senha etc.
        raise DanfeErro(f"Não foi possível abrir o PDF: {exc}") from exc

    if len(pagina.texto.strip()) < 50:
        raise DanfeErro("PDF sem texto (provavelmente digitalizado). Seria necessário OCR.")

    dados = DadosDanfe()
    dados.chave_acesso = _achar_chave(pagina.texto)
    if not dados.chave_acesso:
        raise DanfeErro("Chave de acesso de 44 dígitos não encontrada: o arquivo não parece ser um DANFE.")

    # Dados embutidos na chave: cUF AAMM CNPJ mod série nNF tpEmis cNF DV
    ch = dados.chave_acesso
    dados.emit_uf = UF_POR_CODIGO.get(ch[0:2], "")
    dados.emit_cnpj = ch[6:20]
    dados.modelo = ch[20:22]
    dados.serie = int(ch[22:25])
    dados.numero = int(ch[25:34])

    v = pagina.valor_abaixo
    dados.natureza_operacao = v(["NATUREZA DA OPERAÇÃO"])[:200]
    protocolo = v(["PROTOCOLO DE AUTORIZAÇÃO DE USO", "PROTOCOLO DE AUTORIZAÇÃO"])
    dados.protocolo = protocolo[:60]
    dados.emit_ie = so_digitos(v(["INSCRIÇÃO ESTADUAL"]))[:20]

    if tipo := re.search(r"1\s*-\s*SA[IÍ]DA\s*\n?\s*([01])\b", pagina.texto, re.I):
        dados.tipo_operacao = tipo.group(1)

    dados.dest_nome = v(["NOME / RAZÃO SOCIAL", "NOME/RAZÃO SOCIAL", "RAZÃO SOCIAL"])[:200]
    dados.dest_documento = so_digitos(v(["CNPJ / CPF", "CNPJ/CPF"]))[:14]
    dados.dest_municipio = v(["MUNICÍPIO"])[:100]
    uf = v(["UF"]).strip().upper()
    dados.dest_uf = uf if re.fullmatch(r"[A-Z]{2}", uf) else ""
    dados.data_emissao = _data(v(["DATA DA EMISSÃO", "DATA DE EMISSÃO", "DATA EMISSÃO"]))
    dados.data_saida = _data(
        v(["DATA DA SAÍDA/ENTRADA", "DATA DE SAÍDA/ENTRADA", "DATA SAÍDA/ENTRADA", "DATA DA ENTRADA/SAÍDA", "DATA ENTRADA/SAÍDA"])
    )
    if not dados.data_emissao and (d := _data(protocolo)):
        dados.data_emissao = d
        dados.pendencias.append("data de emissão estimada pela data do protocolo")

    _emitente(pagina, dados)

    # Valores e impostos
    plano_b = None
    for campo, rotulos in ROTULOS_VALORES.items():
        valor = _dinheiro(v(rotulos))
        if valor is None:
            if plano_b is None:
                plano_b = _valores_por_ordem(pagina.texto)
            valor = plano_b.get(campo)
        if valor is None:
            dados.pendencias.append(f"{campo} não localizado")
        else:
            dados.valores[campo] = valor

    if not dados.emit_nome:
        dados.pendencias.append("razão social do emitente não localizada")
    if not dados.data_emissao:
        dados.pendencias.append("data de emissão não localizada")
    return dados
