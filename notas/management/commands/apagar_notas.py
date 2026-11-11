from django.core.management.base import BaseCommand

from notas.importador import apagar_notas, sincronizar_pasta
from notas.models import Emitente, NotaFiscal


class Command(BaseCommand):
    help = "Apaga todas as notas do banco para refazer a importação. Os PDFs da pasta não são alterados."

    def add_arguments(self, parser):
        parser.add_argument("--sim", action="store_true", help="Não pede confirmação")
        parser.add_argument("--manter-emitentes", action="store_true", help="Preserva o cadastro de emitentes")
        parser.add_argument("--historico", action="store_true", help="Apaga também o histórico de importações")
        parser.add_argument("--reimportar", action="store_true", help="Importa a pasta de novo logo em seguida")

    def handle(self, *args, **opcoes):
        notas = NotaFiscal.objects.count()
        emitentes = 0 if opcoes["manter_emitentes"] else Emitente.objects.count()
        self.stdout.write(f"Serão apagados: {notas} nota(s) e {emitentes} emitente(s).")

        if not opcoes["sim"]:
            resposta = input("Esta ação não pode ser desfeita. Digite APAGAR para confirmar: ")
            if resposta.strip() != "APAGAR":
                self.stdout.write("Cancelado. Nada foi apagado.")
                return

        r = apagar_notas(manter_emitentes=opcoes["manter_emitentes"], apagar_historico=opcoes["historico"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Apagados: {r['notas']} nota(s), {r['emitentes']} emitente(s), "
                f"{r['historico']} registro(s) de histórico."
            )
        )

        if opcoes["reimportar"]:
            s = sincronizar_pasta()
            if s.mensagem:
                self.stderr.write(self.style.ERROR(s.mensagem))
                return
            self.stdout.write(
                self.style.SUCCESS(
                    f"{s.arquivos} PDF(s) na pasta | {s.importadas} importada(s) | "
                    f"{s.com_problema} com problema | {s.duplicadas} duplicada(s)"
                )
            )
