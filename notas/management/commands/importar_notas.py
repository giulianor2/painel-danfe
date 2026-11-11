from django.conf import settings
from django.core.management.base import BaseCommand

from notas.importador import sincronizar_pasta


class Command(BaseCommand):
    help = "Varre a pasta de DANFEs uma vez e importa os PDFs novos (ideal para agendador/cron)."

    def add_arguments(self, parser):
        parser.add_argument("--pasta", help="Pasta a varrer (padrão: DANFE_PASTA do .env)")

    def handle(self, *args, **opcoes):
        pasta = opcoes["pasta"] or settings.DANFE_PASTA
        r = sincronizar_pasta(pasta)
        if r.mensagem:
            self.stderr.write(self.style.ERROR(r.mensagem))
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"{r.arquivos} PDF(s) na pasta | {r.importadas} importada(s) | "
                f"{r.com_problema} com problema | {r.duplicadas} duplicada(s)"
            )
        )
