from django.contrib import admin

from .models import Emitente, NotaFiscal, Sincronizacao


@admin.register(Emitente)
class EmitenteAdmin(admin.ModelAdmin):
    list_display = ("razao_social", "cnpj", "municipio", "uf")
    search_fields = ("razao_social", "cnpj")


@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ("numero", "serie", "emitente", "data_emissao", "valor_total", "status")
    list_filter = ("status", "data_emissao")
    search_fields = ("numero", "chave_acesso", "emitente__razao_social", "arquivo")


@admin.register(Sincronizacao)
class SincronizacaoAdmin(admin.ModelAdmin):
    list_display = ("executada_em", "arquivos_na_pasta", "importadas", "com_problema", "duplicadas", "mensagem")
