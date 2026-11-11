"""Importa para o banco os PDFs de DANFE encontrados na pasta configurada."""
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .danfe import DanfeErro
from .leitor import ler_documento
from .models import Emitente, NotaFiscal, Sincronizacao

log = logging.getLogger(__name__)


@dataclass
class Resultado:
    arquivos: int = 0
    importadas: int = 0
    com_problema: int = 0
    duplicadas: int = 0
    mensagem: str = ""

    @property
    def houve_novidade(self):
        return bool(self.importadas or self.com_problema or self.duplicadas or self.mensagem)


def _hash(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _importar_arquivo(caminho: Path, relativo: str, digest: str, resultado: Resultado):
    try:
        dados = ler_documento(caminho)
    except DanfeErro as erro:
        NotaFiscal.objects.create(
            arquivo=relativo, arquivo_hash=digest, status=NotaFiscal.Status.ERRO, observacao=str(erro)[:500]
        )
        resultado.com_problema += 1
        return

    if dados.chave_acesso:
        existente = NotaFiscal.objects.filter(chave_acesso=dados.chave_acesso).first()
    else:
        # NFS-e municipal antiga não tem chave: identifica por prestador + número + código de verificação.
        existente = NotaFiscal.objects.filter(
            tipo_documento=dados.tipo_documento,
            emitente__cnpj=dados.emit_cnpj,
            numero=dados.numero,
            codigo_verificacao=dados.extras.get("codigo_verificacao", ""),
        ).first()
    if existente:
        # Mesmo documento salvo em outro arquivo: registramos só para não reler toda vez.
        NotaFiscal.objects.create(
            arquivo=relativo,
            arquivo_hash=digest,
            status=NotaFiscal.Status.ERRO,
            observacao=f"Duplicada: mesma nota do arquivo {existente.arquivo}.",
        )
        resultado.duplicadas += 1
        return

    with transaction.atomic():
        emitente, _ = Emitente.objects.get_or_create(cnpj=dados.emit_cnpj)
        # Completa o cadastro do emitente com o que este DANFE trouxe.
        atualizou = False
        for campo, valor in {
            "razao_social": dados.emit_nome[:200],
            "inscricao_estadual": dados.emit_ie,
            "inscricao_municipal": dados.emit_im,
            "endereco": dados.emit_endereco,
            "municipio": dados.emit_municipio[:100],
            "uf": dados.emit_uf,
            "cep": dados.emit_cep,
            "telefone": dados.emit_telefone[:20],
        }.items():
            if valor and not getattr(emitente, campo):
                setattr(emitente, campo, valor)
                atualizou = True
        if atualizou:
            emitente.save()

        NotaFiscal.objects.create(
            arquivo=relativo,
            arquivo_hash=digest,
            status=NotaFiscal.Status.PARCIAL if dados.pendencias else NotaFiscal.Status.OK,
            observacao="; ".join(dados.pendencias)[:500],
            tipo_documento=dados.tipo_documento,
            chave_acesso=dados.chave_acesso or None,
            numero=dados.numero,
            serie=dados.serie,
            modelo=dados.modelo,
            tipo_operacao=dados.tipo_operacao,
            natureza_operacao=dados.natureza_operacao,
            protocolo=dados.protocolo,
            data_emissao=dados.data_emissao,
            data_saida=dados.data_saida,
            emitente=emitente,
            dest_nome=dados.dest_nome,
            dest_documento=dados.dest_documento,
            dest_municipio=dados.dest_municipio,
            dest_uf=dados.dest_uf,
            **dados.valores,
            **dados.extras,
        )
    if dados.pendencias:
        resultado.com_problema += 1
    else:
        resultado.importadas += 1


def sincronizar_pasta(pasta=None) -> Resultado:
    """Varre a pasta (e subpastas) e importa os PDFs ainda não conhecidos."""
    pasta = Path(pasta or settings.DANFE_PASTA)
    resultado = Resultado()
    if not pasta.is_dir():
        resultado.mensagem = f"Pasta não encontrada: {pasta}"
        _registrar(resultado, sempre=False)
        return resultado

    arquivos = sorted(p for p in pasta.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    resultado.arquivos = len(arquivos)
    conhecidos = set(NotaFiscal.objects.values_list("arquivo_hash", flat=True))

    for caminho in arquivos:
        try:
            digest = _hash(caminho)
        except OSError:  # arquivo ainda sendo copiado para a pasta; tenta na próxima varredura
            continue
        if digest in conhecidos:
            continue
        conhecidos.add(digest)
        try:
            _importar_arquivo(caminho, caminho.relative_to(pasta).as_posix(), digest, resultado)
        except Exception:  # um arquivo ruim não pode parar a fila
            log.exception("Falha inesperada ao importar %s", caminho)
            resultado.com_problema += 1

    _registrar(resultado)
    return resultado


def apagar_notas(manter_emitentes=False, apagar_historico=False) -> dict:
    """Apaga todas as notas do banco para permitir importar tudo de novo.

    Os PDFs da pasta não são tocados: na próxima varredura eles são lidos como novos.
    Devolve a quantidade apagada de cada tipo de registro.
    """
    with transaction.atomic():
        apagados = {"notas": NotaFiscal.objects.all().delete()[0], "emitentes": 0, "historico": 0}
        if not manter_emitentes:
            apagados["emitentes"] = Emitente.objects.all().delete()[0]
        if apagar_historico:
            apagados["historico"] = Sincronizacao.objects.all().delete()[0]
    return apagados


def _registrar(resultado: Resultado, sempre=True):
    if not resultado.houve_novidade:
        return
    if not sempre:
        # Evita gravar a mesma mensagem de erro a cada varredura.
        ultima = Sincronizacao.objects.first()
        if ultima and ultima.mensagem == resultado.mensagem[:300]:
            return
    Sincronizacao.objects.create(
        arquivos_na_pasta=resultado.arquivos,
        importadas=resultado.importadas,
        com_problema=resultado.com_problema,
        duplicadas=resultado.duplicadas,
        mensagem=resultado.mensagem[:300],
    )
