"""Leitura de notas fiscais de SERVIÇO (NFS-e) em PDF.

Dois layouts são reconhecidos:

1. DANFSe v1.0, o padrão nacional (tem "Chave de Acesso da NFS-e" com 50 dígitos).
   Grade de rótulo em cima e valor embaixo, lida por posição.
2. NFS-e municipal no modelo "PRESTADOR DE SERVIÇOS / TOMADOR DE SERVIÇOS" com campos
   no formato "Rótulo: valor" (ex.: Prefeitura de Divinópolis antes do padrão nacional).

Cada prefeitura que ainda não usa o padrão nacional tem um desenho próprio de nota;
outros modelos precisam de um leitor novo neste arquivo.
"""
from __future__ import annotations

import re
from decimal import Decimal

from .danfe import DadosDanfe, DanfeErro, Pagina, _data, _dinheiro, _norm, chave_valida, so_digitos

ZERO = Decimal("0")


def _valor(texto: str) -> Decimal | None:
    """ "R$ 750,00" -> 750.00 ; "-" ou vazio -> None"""
    return _dinheiro(texto)


def _municipio_uf(texto: str):
    """ "Divinópolis - MG" -> ("Divinópolis", "MG")"""
    achado = re.match(r"\s*(.+?)\s*[-/]\s*([A-Za-z]{2})\s*$", texto or "")
    if achado:
        return achado.group(1).strip(), achado.group(2).upper()
    return (texto or "").strip(" -"), ""


def _limpo(texto: str) -> str:
    texto = " ".join((texto or "").split())
    return "" if texto in ("-", "–") else texto


def _fechar(dados: DadosDanfe):
    """Pendências comuns aos dois layouts."""
    if not dados.numero:
        dados.pendencias.append("número da nota não localizado")
    if not dados.emit_cnpj:
        raise DanfeErro("CNPJ/CPF do prestador não encontrado na nota de serviço.")
    if not dados.emit_nome:
        dados.pendencias.append("nome do prestador não localizado")
    if not dados.data_emissao:
        dados.pendencias.append("data de emissão não localizada")
    if "valor_total" not in dados.valores:
        dados.pendencias.append("valor do serviço não localizado")
    return dados


# --------------------------------------------------------------------------
# 1. DANFSe (padrão nacional)
# --------------------------------------------------------------------------
def ler_danfse(page) -> DadosDanfe:
    pagina = Pagina(page, x_tolerance=0.6)  # neste layout as palavras ficam muito próximas
    dados = DadosDanfe(tipo_documento="NFSE")

    def v(rotulo, ocorrencia=0, **kw):
        return _limpo(pagina.valor_abaixo([rotulo], ocorrencia, alcance=12, **kw))

    for achado in re.finditer(r"(?<!\d)\d{50}(?!\d)", pagina.texto):
        if chave_valida(achado.group(), 50):
            dados.chave_acesso = achado.group()
            break
    if not dados.chave_acesso:
        dados.pendencias.append("chave de acesso (50 dígitos) não localizada")

    numero = so_digitos(v("Número da NFS-e"))
    if numero:
        dados.numero = int(numero)
    elif dados.chave_acesso:
        dados.numero = int(dados.chave_acesso[23:36])  # o número também está dentro da chave
    serie = so_digitos(v("Série da DPS"))
    dados.serie = int(serie) if serie else None
    dados.data_emissao = _data(v("Data e Hora da emissão da NFS-e"))
    dados.extras["data_competencia"] = _data(v("Competência da NFS-e"))

    # Prestador (1ª ocorrência dos rótulos) e tomador (2ª)
    dados.emit_cnpj = so_digitos(v("CNPJ / CPF / NIF"))[:14]
    if not dados.emit_cnpj and dados.chave_acesso:
        dados.emit_cnpj = dados.chave_acesso[9:23]
    dados.emit_im = so_digitos(v("Inscrição Municipal"))[:20]
    dados.emit_telefone = v("Telefone")[:20]
    dados.emit_nome = v("Nome / Nome Empresarial")[:200]
    dados.emit_endereco = v("Endereço", multilinha=True)[:300]
    dados.emit_municipio, dados.emit_uf = _municipio_uf(v("Município"))
    dados.emit_cep = so_digitos(v("CEP"))[:8]

    dados.dest_documento = so_digitos(v("CNPJ / CPF / NIF", 1))[:14]
    dados.dest_nome = v("Nome / Nome Empresarial", 1)[:200]
    dados.dest_municipio, dados.dest_uf = _municipio_uf(v("Município", 1))
    dados.dest_municipio = dados.dest_municipio[:100]

    # Serviço
    dados.extras["codigo_servico"] = v("Código de Tributação Nacional", multilinha=True)[:200]
    dados.extras["local_prestacao"] = v("Local da Prestação")[:100]
    dados.extras["discriminacao"] = v("Descrição do Serviço", multilinha=True)
    dados.natureza_operacao = v("Tributação do ISSQN")[:200]
    dados.extras["situacao"] = "Cancelada" if "CANCELAD" in _norm(pagina.texto) else "Normal"

    # Valores
    servico = _valor(v("Valor do Serviço"))
    if servico is not None:
        dados.valores["valor_total"] = servico
        dados.valores["valor_produtos"] = servico
    desconto = (_valor(v("Desconto Incondicionado")) or ZERO) + (_valor(v("Desconto Condicionado")) or ZERO)
    dados.valores["valor_desconto"] = desconto
    dados.valores["valor_deducoes"] = _valor(v("Total Deduções/Reduções")) or ZERO
    dados.valores["base_iss"] = _valor(v("BC ISSQN")) or ZERO
    dados.valores["valor_iss"] = _valor(v("ISSQN Apurado")) or ZERO
    aliquota = re.search(r"\d+(?:,\d+)?", v("Alíquota Aplicada"))
    dados.valores["aliquota_iss"] = Decimal(aliquota.group().replace(",", ".")) if aliquota else ZERO
    retencao = _norm(v("Retenção do ISSQN"))
    dados.extras["iss_retido"] = bool(retencao) and not retencao.startswith("NAO")
    dados.valores["valor_ir"] = _valor(v("IRRF")) or ZERO
    dados.valores["valor_inss"] = _valor(v("Contribuição Previdenciária - Retida")) or ZERO
    # PIS/COFINS/CSLL retidos vêm somados neste layout ("Contribuições Sociais - Retidas").
    dados.valores["valor_outras_retencoes"] = _valor(v("Contribuições Sociais - Retidas")) or ZERO
    liquido = _valor(v("Valor Líquido da NFS-e"))
    if liquido is not None:
        dados.valores["valor_liquido"] = liquido
    elif servico is not None:
        dados.valores["valor_liquido"] = servico
    return _fechar(dados)


# --------------------------------------------------------------------------
# 2. NFS-e municipal ("Rótulo: valor")
# --------------------------------------------------------------------------
def _entre(texto: str, inicio: str, fim: str) -> str:
    achado = re.search(rf"{inicio}(.*?){fim}", texto, re.S | re.I)
    return achado.group(1) if achado else ""


def _campo(bloco: str, rotulo: str, ate: str = r"$") -> str:
    """Valor de "Rótulo: valor" dentro de uma linha, parando no próximo rótulo."""
    achado = re.search(rf"{rotulo}[ \t]*:[ \t]*(.*?)[ \t]*(?:{ate})", bloco, re.I | re.M)
    return _limpo(achado.group(1)) if achado else ""


def _parte(bloco: str):
    """Extrai os campos de um bloco PRESTADOR ou TOMADOR."""
    logradouro = _campo(bloco, "Endereço", r"Número\s*:|$")
    numero = _campo(bloco, "Número", r"Bairro\s*:|$")
    bairro = _campo(bloco, "Bairro", r"CEP\s*:|$")
    complemento = _campo(bloco, "Complemento")
    endereco = ", ".join(p for p in [logradouro, numero, complemento, bairro] if p)
    return {
        "nome": _campo(bloco, r"Nome/Razão social", r"Inscrição estadual\s*:|$"),
        "documento": so_digitos(_campo(bloco, r"CPF/CNPJ", r"Inscrição municipal\s*:|$"))[:14],
        "im": so_digitos(_campo(bloco, r"Inscrição municipal", r"Telefone\s*:|Inscrição estadual\s*:|$"))[:20],
        "ie": so_digitos(_campo(bloco, r"Inscrição estadual", r"$"))[:20],
        "telefone": _campo(bloco, "Telefone", r"Celular\s*:|$")[:20],
        "endereco": endereco[:300],
        "cep": so_digitos(_campo(bloco, "CEP"))[:8],
        "municipio": _campo(bloco, "Município", r"UF\s*:|$")[:100],
        "uf": _campo(bloco, "UF")[:2].upper(),
    }


def ler_nfse_municipal(page) -> DadosDanfe:
    pagina = Pagina(page)
    texto = pagina.texto
    dados = DadosDanfe(tipo_documento="NFSE")

    def topo(rotulo):  # cabeçalho: valor alinhado à direita, abaixo do rótulo
        return _limpo(pagina.valor_abaixo([rotulo], alcance=18, fonte_maior=False))

    numero = so_digitos(topo("Número da nota"))
    dados.numero = int(numero) if numero else None
    dados.data_emissao = _data(topo("Data da emissão da nota"))
    dados.extras["data_competencia"] = _data(topo("Data do fato gerador"))
    dados.extras["codigo_verificacao"] = topo("Código de verificação")[:20]

    prestador = _parte(_entre(texto, r"PRESTADOR DE SERVIÇOS", r"TOMADOR DE SERVIÇOS"))
    tomador = _parte(_entre(texto, r"TOMADOR DE SERVIÇOS", r"DISCRIMINAÇÃO DOS SERVIÇOS"))
    dados.emit_nome, dados.emit_cnpj = prestador["nome"][:200], prestador["documento"]
    dados.emit_im, dados.emit_ie = prestador["im"], prestador["ie"]
    dados.emit_telefone, dados.emit_endereco = prestador["telefone"], prestador["endereco"]
    dados.emit_cep, dados.emit_municipio, dados.emit_uf = prestador["cep"], prestador["municipio"], prestador["uf"]
    dados.dest_nome, dados.dest_documento = tomador["nome"][:200], tomador["documento"]
    dados.dest_municipio, dados.dest_uf = tomador["municipio"], tomador["uf"]

    # Discriminação: linhas entre o cabeçalho da tabela e "Forma de Pagamento" / "RETENÇÕES"
    bloco = _entre(texto, r"DISCRIMINAÇÃO DOS SERVIÇOS", r"Forma de Pagamento|RETENÇÕES FEDERAIS")
    descricoes = []
    for linha in bloco.splitlines():
        linha = linha.strip()
        if not linha or _norm(linha).startswith("VALORUNITARIO"):
            continue
        # tira as colunas numéricas do fim: unitário, qtd, valor, "base x alíquota = ISS"
        descricoes.append(re.sub(r"\s+[\d.]+,\d{2,4}\s+[\d.]+,\d{2,4}\s+[\d.]+,\d{2,4}.*$", "", linha).strip(" ."))
        if aliquota := re.search(r"x\s*(\d+,\d+)\s*=", linha):
            dados.valores["aliquota_iss"] = Decimal(aliquota.group(1).replace(",", "."))
    dados.extras["discriminacao"] = "; ".join(d for d in descricoes if d)
    dados.extras["codigo_servico"] = _limpo(_entre(texto, r"Códigos? dos? serviços?:", r"Desc\. condicionado"))[:200]
    dados.natureza_operacao = _campo(texto, "Natureza da operação")[:200]
    dados.extras["local_prestacao"] = _campo(texto, "Local da prestação do serviço")[:100]
    dados.extras["situacao"] = _campo(texto, r"Situação desta NFS-e")[:30] or "Normal"

    # Retenções federais: linha de 6 valores após os títulos
    if ret := re.search(r"PIS/PASEP\s+COFINS\s+INSS\s+IR\s+CSLL\s+Outras retenções\s*\n(.+)", texto):
        valores = [_dinheiro(x) for x in re.findall(r"[\d.]+,\d{2}", ret.group(1))]
        campos = ["valor_pis", "valor_cofins", "valor_inss", "valor_ir", "valor_csll", "valor_outras_retencoes"]
        if len(valores) == 6:
            dados.valores.update(dict(zip(campos, valores)))
    if bruto := re.search(r"Valor bruto\s*=\s*R\$\s*([\d.]+,\d{2})", texto):
        dados.valores["valor_total"] = dados.valores["valor_produtos"] = _dinheiro(bruto.group(1))
    if liquido := re.search(r"Valor líquido\s*=\s*R\$\s*([\d.]+,\d{2})", texto):
        dados.valores["valor_liquido"] = _dinheiro(liquido.group(1))
    # Linha: desc. condicionado | desc. incondicionado | deduções | base de cálculo | valor ISS
    if iss := re.search(r"Valor ISS\(R\$\)\s*\n(.+)", texto):
        valores = [_dinheiro(x) for x in re.findall(r"[\d.]+,\d{2}", iss.group(1))]
        if len(valores) == 5:
            dados.valores["valor_desconto"] = valores[0] + valores[1]
            dados.valores["valor_deducoes"] = valores[2]
            dados.valores["base_iss"] = valores[3]
            dados.valores["valor_iss"] = valores[4]
    if "valor_iss" not in dados.valores:
        dados.pendencias.append("valor do ISS não localizado")
    return _fechar(dados)
