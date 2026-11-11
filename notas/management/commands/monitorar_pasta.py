from django.conf import settings
from django.core.management.base import BaseCommand

from notas import monitor


class Command(BaseCommand):
    help = "Fica em execução importando automaticamente os PDFs que chegarem na pasta."

    def add_arguments(self, parser):
        parser.add_argument("--intervalo", type=int, help="Segundos entre as verificações")

    def handle(self, *args, **opcoes):
        intervalo = opcoes["intervalo"] or settings.DANFE_MONITOR_INTERVALO
        self.stdout.write(f"Monitorando {settings.DANFE_PASTA} a cada {intervalo}s (Ctrl+C para parar)")

        def avisar(r):
            self.stdout.write(
                r.mensagem or f"+{r.importadas} importada(s), {r.com_problema} com problema, {r.duplicadas} duplicada(s)"
            )

        try:
            monitor.laco(intervalo=intervalo, ao_importar=avisar)
        except KeyboardInterrupt:
            self.stdout.write("Monitor encerrado.")
