"""Monitor da pasta: verifica periodicamente se chegaram PDFs novos."""
import logging
import threading
import time

from django.conf import settings
from django.db import close_old_connections

log = logging.getLogger(__name__)
_iniciado = False


def laco(intervalo=None, parar: threading.Event | None = None, ao_importar=None):
    from .importador import sincronizar_pasta

    intervalo = intervalo or settings.DANFE_MONITOR_INTERVALO
    while not (parar and parar.is_set()):
        try:
            close_old_connections()
            resultado = sincronizar_pasta()
            if resultado.houve_novidade and ao_importar:
                ao_importar(resultado)
        except Exception:
            log.exception("Erro na varredura da pasta de notas")
        finally:
            close_old_connections()
        if parar:
            parar.wait(intervalo)
        else:
            time.sleep(intervalo)


def iniciar_em_segundo_plano():
    """Sobe o monitor numa thread junto com o servidor de desenvolvimento."""
    global _iniciado
    if _iniciado:
        return
    _iniciado = True
    threading.Thread(target=laco, name="monitor-danfe", daemon=True).start()
