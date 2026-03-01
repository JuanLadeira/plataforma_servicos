"""
Resources para django-import-export.

Estrutura de dependências para importação:
1. Categoria - não depende de nada (além de Empresa)
2. Atributo - depende de Categoria
3. ValorAtributo - depende de Atributo
4. Produto - depende de Categoria e Empresa
5. VariacaoProduto - depende de Produto e ValorAtributo

Para importar variações, os produtos JÁ DEVEM EXISTIR.
Os valores de atributo também devem existir para o M2M.
"""

from import_export import fields, resources, widgets
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.produto.models import (
    Atributo,
    Categoria,
    Produto,
    ValorAtributo,
    VariacaoProduto,
)


class TenantForeignKeyWidget(ForeignKeyWidget):
    """
    Widget personalizado que filtra por empresa/tenant.
    Útil para lookups em contexto multi-tenant.
    """

    def __init__(self, model, field="pk", empresa=None, **kwargs):
        super().__init__(model, field, **kwargs)
        self.empresa = empresa

    def get_queryset(self, value, row, *args, **kwargs):
        qs = super().get_queryset(value, row, *args, **kwargs)
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        return qs


class CategoriaResource(resources.ModelResource):
    """
    Resource para importação/exportação de Categorias.

    Campos do CSV:
    - categoria: Nome da categoria (obrigatório)
    - empresa: Slug ou ID da empresa (obrigatório para import)
    """

    empresa = fields.Field(
        column_name="empresa",
        attribute="empresa",
        widget=ForeignKeyWidget(Empresa, field="slug"),
    )

    class Meta:
        model = Categoria
        fields = ("id", "categoria", "empresa")
        export_order = ("id", "categoria", "empresa")
        import_id_fields = ("categoria", "empresa")
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        """Normaliza dados antes da importação."""
        if "categoria" in row:
            row["categoria"] = row["categoria"].strip()


class AtributoResource(resources.ModelResource):
    """
    Resource para importação/exportação de Atributos.

    Campos do CSV:
    - nome: Nome do atributo (ex: "Cor", "Tamanho")
    - categoria: Nome da categoria pai
    - multipla_selecao: True/False

    A categoria DEVE existir antes da importação.
    """

    categoria = fields.Field(
        column_name="categoria",
        attribute="categoria",
        widget=ForeignKeyWidget(Categoria, field="categoria"),
    )

    class Meta:
        model = Atributo
        fields = ("id", "nome", "categoria", "multipla_selecao")
        export_order = ("id", "nome", "categoria", "multipla_selecao")
        import_id_fields = ("nome", "categoria")
        skip_unchanged = True
        report_skipped = True


class ValorAtributoResource(resources.ModelResource):
    """
    Resource para importação/exportação de Valores de Atributo.

    Campos do CSV:
    - valor: Valor do atributo (ex: "Vermelho", "P", "42")
    - atributo: Nome do atributo (ex: "Cor")
    - preco_adicional: Valor adicional fixo (opcional)
    - percentual_adicional: Percentual adicional (opcional)

    O atributo DEVE existir antes da importação.
    """

    atributo = fields.Field(
        column_name="atributo",
        attribute="atributo",
        widget=ForeignKeyWidget(Atributo, field="nome"),
    )

    class Meta:
        model = ValorAtributo
        fields = ("id", "valor", "atributo", "preco_adicional", "percentual_adicional")
        export_order = ("id", "atributo", "valor", "preco_adicional", "percentual_adicional")
        import_id_fields = ("valor", "atributo")
        skip_unchanged = True
        report_skipped = True


class ProdutoResource(resources.ModelResource):
    """
    Resource para importação/exportação de Produtos.

    Campos do CSV:
    - produto: Nome do produto (obrigatório)
    - categoria: Nome da categoria (opcional)
    - empresa: Slug da empresa (obrigatório para import)
    - ncm: Código NCM (obrigatório)
    - preco: Preço do produto
    - estoque: Quantidade em estoque
    - estoque_minimo: Estoque mínimo
    - disponivel: True/False
    - importado: True/False
    - descricao: Descrição do produto

    A categoria e empresa DEVEM existir antes da importação.
    """

    categoria = fields.Field(
        column_name="categoria",
        attribute="categoria",
        widget=ForeignKeyWidget(Categoria, field="categoria"),
    )
    empresa = fields.Field(
        column_name="empresa",
        attribute="empresa",
        widget=ForeignKeyWidget(Empresa, field="slug"),
    )

    class Meta:
        model = Produto
        fields = (
            "id",
            "produto",
            "categoria",
            "empresa",
            "ncm",
            "preco",
            "estoque",
            "estoque_minimo",
            "disponivel",
            "importado",
            "descricao",
        )
        export_order = (
            "id",
            "empresa",
            "produto",
            "categoria",
            "ncm",
            "preco",
            "estoque",
            "estoque_minimo",
            "disponivel",
            "importado",
            "descricao",
        )
        import_id_fields = ("produto", "empresa")
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        """Normaliza dados antes da importação."""
        if "produto" in row:
            row["produto"] = row["produto"].strip()
        if "ncm" in row:
            row["ncm"] = str(row["ncm"]).strip()


class ProdutoSlugWidget(ForeignKeyWidget):
    """
    Widget personalizado para buscar Produto por slug.
    Considera também a empresa para garantir unicidade.
    """

    def __init__(self, model, field="slug", empresa_field=None):
        super().__init__(model, field)
        self.empresa_field = empresa_field

    def get_queryset(self, value, row, *args, **kwargs):
        qs = super().get_queryset(value, row, *args, **kwargs)
        # Se tiver empresa no row, filtra por ela
        if self.empresa_field and self.empresa_field in row:
            empresa_slug = row[self.empresa_field]
            if empresa_slug:
                qs = qs.filter(empresa__slug=empresa_slug)
        return qs


class ValorAtributoM2MWidget(ManyToManyWidget):
    """
    Widget para M2M de ValorAtributo.
    Espera valores no formato "Atributo:Valor" separados por vírgula.
    Ex: "Cor:Vermelho, Tamanho:P"
    """

    def __init__(self, model=ValorAtributo, separator=",", field="pk"):
        super().__init__(model, separator=separator, field=field)

    def clean(self, value, row=None, **kwargs):
        if not value:
            return self.model.objects.none()

        # Parse valores no formato "Atributo:Valor"
        valores_ids = []
        for item in str(value).split(self.separator):
            item = item.strip()
            if ":" in item:
                atributo_nome, valor = item.split(":", 1)
                try:
                    valor_obj = ValorAtributo.objects.get(
                        atributo__nome__iexact=atributo_nome.strip(),
                        valor__iexact=valor.strip(),
                    )
                    valores_ids.append(valor_obj.pk)
                except ValorAtributo.DoesNotExist:
                    pass  # Ignora valores não encontrados

        return self.model.objects.filter(pk__in=valores_ids)

    def render(self, value, obj=None):
        if value is None:
            return ""
        return self.separator.join(
            f"{v.atributo.nome}:{v.valor}" for v in value.all()
        )


class VariacaoProdutoResource(resources.ModelResource):
    """
    Resource para importação/exportação de Variações de Produto.

    Campos do CSV:
    - produto_slug: Slug do produto pai (obrigatório)
    - empresa: Slug da empresa (para filtrar produto)
    - sku: SKU da variação (opcional - gerado automaticamente)
    - preco: Preço específico da variação (opcional)
    - estoque: Quantidade em estoque
    - valores: Valores de atributo no formato "Atributo:Valor, Atributo:Valor"
              Ex: "Cor:Vermelho, Tamanho:P"

    O produto DEVE existir antes da importação.
    Os valores de atributo DEVEM existir antes da importação.

    IMPORTANTE: Para importar variações corretamente:
    1. Primeiro importe/crie as Categorias
    2. Depois importe/crie os Atributos
    3. Depois importe/crie os Valores de Atributo
    4. Depois importe/crie os Produtos
    5. Por último, importe as Variações
    """

    produto = fields.Field(
        column_name="produto_slug",
        attribute="produto",
        widget=ProdutoSlugWidget(Produto, field="slug", empresa_field="empresa"),
    )
    valores = fields.Field(
        column_name="valores",
        attribute="valores",
        widget=ValorAtributoM2MWidget(ValorAtributo, separator=","),
    )

    class Meta:
        model = VariacaoProduto
        fields = ("id", "produto", "sku", "preco", "estoque", "valores")
        export_order = ("id", "produto", "sku", "preco", "estoque", "valores")
        import_id_fields = ("sku",)
        skip_unchanged = True
        report_skipped = True

    def after_save_instance(self, instance, using_transactions, dry_run):
        """Gera o SKU após salvar a instância com os valores M2M."""
        if not dry_run and not instance.sku:
            instance.gerar_sku()


# Resources simplificados para tenant-aware admin
class TenantAwareProdutoResource(ProdutoResource):
    """
    Resource de Produto que recebe a empresa do contexto.
    Usado no admin do gerente onde a empresa é determinada pelo usuário.
    """

    def __init__(self, empresa=None, **kwargs):
        super().__init__(**kwargs)
        self.empresa = empresa

    def before_import_row(self, row, **kwargs):
        super().before_import_row(row, **kwargs)
        # Injeta a empresa do contexto se não estiver no CSV
        if self.empresa and not row.get("empresa"):
            row["empresa"] = self.empresa.slug

    def get_queryset(self):
        qs = super().get_queryset()
        if self.empresa:
            qs = qs.filter(empresa=self.empresa)
        return qs


class TenantAwareVariacaoResource(VariacaoProdutoResource):
    """
    Resource de Variação que recebe a empresa do contexto.
    """

    def __init__(self, empresa=None, **kwargs):
        super().__init__(**kwargs)
        self.empresa = empresa

    def before_import_row(self, row, **kwargs):
        # Injeta a empresa para o widget de produto
        if self.empresa and not row.get("empresa"):
            row["empresa"] = self.empresa.slug

    def get_queryset(self):
        qs = super().get_queryset()
        if self.empresa:
            qs = qs.filter(produto__empresa=self.empresa)
        return qs
