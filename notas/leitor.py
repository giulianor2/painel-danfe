"""Porta de entrada da leitura: identifica o tipo de documento e chama o leitor certo."""
from pathlib import Path

import pdfplumber

from . import danfe, nfse
from .danfe import DadosDanfe, DanfeErro, _norm


def ler_documento(caminho: str | Path) -> DadosDanfe:
    try:
        with pdfplumber.open(str(caminho)) as pdf:
            if not pdf.pages:
                raise DanfeErro("PDF sem páginas.")
            page = pdf.pages[0]
            texto = page.extract_text() or ""
            if len(texto.strip()) < 50:
                raise DanfeErro("PDF sem texto (provavelmente digitalizado). Seria necessário OCR.")
            marca = _norm(texto)
            if "DANFSE" in marca or "CHAVEDEACESSODANFSE" in marca:
                return nfse.ler_danfse(page)
            if "PRESTADORDESERVICOS" in marca and "TOMADORDESERVICOS" in marca:
                return nfse.ler_nfse_municipal(page)
            if "DANFE" not in marca and "TOMADOR" in marca and ("NFSE" in marca or "ISSQN" in marca):
                raise DanfeErro(
                    "Parece uma nota de serviço (NFS-e) em um modelo de prefeitura ainda não suportado."
                )
    except DanfeErro:
        raise
    except Exception as exc:  # PDF corrompido, protegido por senha etc.
        raise DanfeErro(f"Não foi possível abrir o PDF: {exc}") from exc
    return danfe.ler_danfe(caminho)
