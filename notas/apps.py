import os
import sys

from django.apps import AppConfig
from django.conf import settings


class NotasConfig(AppConfig):
    name = "notas"
    verbose_name = "Notas fiscais"

    def ready(self):
        # Com "manage.py runserver" o monitor da pasta sobe junto (uma única vez,
        # no processo filho do autoreload). Em produção use "manage.py monitorar_pasta".
        if not settings.DANFE_MONITOR_AUTOSTART or "runserver" not in sys.argv:
            return
        if os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv:
            from . import monitor

            monitor.iniciar_em_segundo_plano()
