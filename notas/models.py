from django.db import models


class Emitente(models.Model):
    cnpj = models.CharField("CNPJ", max_length=14, unique=True)
    razao_social = models.CharField("razão social", max_length=200, blank=True)
    inscricao_estadual = models.CharField("inscrição estadual", max_length=20, blank=True)
    inscricao_municipal = models.CharField("inscrição municipal", max_length=20, blank=True)
    endereco = models.CharField("endereço", max_length=300, blank=True)
    municipio = models.CharField("município", max_length=100, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=8, blank=True)
    telefone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["razao_social"]

    def __str__(self):
        return self.razao_social or self.cnpj


class NotaFiscal(models.Model):
    class Status(models.TextChoices):
        OK = "OK", "Lida"
        PARCIAL = "PARCIAL", "Leitura parcial"
        ERRO = "ERRO", "Não lida"

    class Tipo(models.TextChoices):
        NFE = "NFE", "Produto (NF-e)"
        NFSE = "NFSE", "Serviço (NFS-e)"

    class TipoOperacao(models.TextChoices):
        ENTRADA = "0", "Entrada"
        SAIDA = "1", "Saída"

    # Arquivo de origem
    arquivo = models.CharField("arquivo", max_length=500, help_text="Caminho relativo à pasta das notas")
    arquivo_hash = models.CharField(max_length=64, unique=True)
    importado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    observacao = models.CharField("observação da leitura", max_length=500, blank=True)

    # Cabeçalho
    tipo_documento = models.CharField("tipo", max_length=4, choices=Tipo.choices, default=Tipo.NFE, db_index=True)
    # NF-e: 44 dígitos. NFS-e padrão nacional: 50 dígitos. NFS-e municipal antiga: sem chave.
    chave_acesso = models.CharField("chave de acesso", max_length=50, unique=True, null=True, blank=True)
    numero = models.PositiveIntegerField("número", null=True, blank=True)
    serie = models.PositiveIntegerField("série", null=True, blank=True)
    modelo = models.CharField(max_length=2, blank=True)
    tipo_operacao = models.CharField("tipo de operação", max_length=1, choices=TipoOperacao.choices, blank=True)
    natureza_operacao = models.CharField("natureza da operação", max_length=200, blank=True)
    protocolo = models.CharField("protocolo de autorização", max_length=60, blank=True)
    data_emissao = models.DateField("data de emissão", null=True, blank=True, db_index=True)
    data_saida = models.DateField("data de saída/entrada", null=True, blank=True)

    # Emitente e destinatário
    emitente = models.ForeignKey(Emitente, on_delete=models.PROTECT, related_name="notas", null=True, blank=True)
    dest_nome = models.CharField("destinatário", max_length=200, blank=True)
    dest_documento = models.CharField("CNPJ/CPF do destinatário", max_length=14, blank=True)
    dest_municipio = models.CharField(max_length=100, blank=True)
    dest_uf = models.CharField(max_length=2, blank=True)

    # Valores e impostos
    base_icms = models.DecimalField("base de cálculo do ICMS", max_digits=15, decimal_places=2, default=0)
    valor_icms = models.DecimalField("valor do ICMS", max_digits=15, decimal_places=2, default=0)
    base_icms_st = models.DecimalField("base de cálculo do ICMS ST", max_digits=15, decimal_places=2, default=0)
    valor_icms_st = models.DecimalField("valor do ICMS ST", max_digits=15, decimal_places=2, default=0)
    valor_ipi = models.DecimalField("valor do IPI", max_digits=15, decimal_places=2, default=0)
    valor_produtos = models.DecimalField("valor dos produtos", max_digits=15, decimal_places=2, default=0)
    valor_frete = models.DecimalField("frete", max_digits=15, decimal_places=2, default=0)
    valor_seguro = models.DecimalField("seguro", max_digits=15, decimal_places=2, default=0)
    valor_desconto = models.DecimalField("desconto", max_digits=15, decimal_places=2, default=0)
    valor_outras = models.DecimalField("outras despesas", max_digits=15, decimal_places=2, default=0)
    valor_total = models.DecimalField("valor total da nota", max_digits=15, decimal_places=2, default=0)

    # Somente nota de serviço (NFS-e). Nela, valor_produtos/valor_total guardam o valor do serviço.
    codigo_verificacao = models.CharField("código de verificação", max_length=20, blank=True)
    data_competencia = models.DateField("competência / fato gerador", null=True, blank=True)
    discriminacao = models.TextField("discriminação do serviço", blank=True)
    codigo_servico = models.CharField("código do serviço", max_length=200, blank=True)
    local_prestacao = models.CharField("local da prestação", max_length=100, blank=True)
    situacao = models.CharField("situação da nota", max_length=30, blank=True)
    base_iss = models.DecimalField("base de cálculo do ISS", max_digits=15, decimal_places=2, default=0)
    aliquota_iss = models.DecimalField("alíquota do ISS (%)", max_digits=5, decimal_places=2, default=0)
    valor_iss = models.DecimalField("valor do ISS", max_digits=15, decimal_places=2, default=0)
    iss_retido = models.BooleanField("ISS retido pelo tomador", default=False)
    valor_deducoes = models.DecimalField("deduções", max_digits=15, decimal_places=2, default=0)
    valor_pis = models.DecimalField("PIS/PASEP retido", max_digits=15, decimal_places=2, default=0)
    valor_cofins = models.DecimalField("COFINS retido", max_digits=15, decimal_places=2, default=0)
    valor_inss = models.DecimalField("INSS retido", max_digits=15, decimal_places=2, default=0)
    valor_ir = models.DecimalField("IR retido", max_digits=15, decimal_places=2, default=0)
    valor_csll = models.DecimalField("CSLL retido", max_digits=15, decimal_places=2, default=0)
    valor_outras_retencoes = models.DecimalField("outras retenções", max_digits=15, decimal_places=2, default=0)
    valor_liquido = models.DecimalField("valor líquido", max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = "nota fiscal"
        verbose_name_plural = "notas fiscais"
        ordering = ["-data_emissao", "-numero"]

    def __str__(self):
        return f"{self.sigla} {self.numero or '?'}"

    @property
    def eh_servico(self):
        return self.tipo_documento == self.Tipo.NFSE

    @property
    def sigla(self):
        return "NFS-e" if self.eh_servico else "NF-e"

    @property
    def cancelada(self):
        return self.situacao.lower().startswith("cancel")

    @property
    def retencoes_federais(self):
        return (
            self.valor_pis + self.valor_cofins + self.valor_inss + self.valor_ir + self.valor_csll
            + self.valor_outras_retencoes
        )

    @property
    def total_impostos(self):
        if self.eh_servico:
            return self.valor_iss + self.retencoes_federais
        return self.valor_icms + self.valor_icms_st + self.valor_ipi


class Sincronizacao(models.Model):
    """Registro de cada varredura da pasta que encontrou algo novo ou falhou."""

    executada_em = models.DateTimeField(auto_now_add=True)
    arquivos_na_pasta = models.PositiveIntegerField(default=0)
    importadas = models.PositiveIntegerField(default=0)
    com_problema = models.PositiveIntegerField(default=0)
    duplicadas = models.PositiveIntegerField(default=0)
    mensagem = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-executada_em"]
        verbose_name = "sincronização"
        verbose_name_plural = "sincronizações"
