from django import forms
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.forms.models import BaseInlineFormSet
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline
from unfold.contrib.forms.widgets import ArrayWidget
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from unfold.decorators import display, action
from django.utils.translation import gettext_lazy as _

from plataforma_de_servicos.core.admin.mixins import RBACAdminMixin
from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.core.admin.mixins import TenantAwareInlineMixin
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.admin.widgets import GroupedCheckboxSelectMultiple
from plataforma_de_servicos.produto.models import Atributo
from plataforma_de_servicos.produto.models import Image
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import ValorAtributo
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.produto.resources import (
    AtributoResource,
    CategoriaResource,
    TenantAwareProdutoResource,
    TenantAwareVariacaoResource,
    ValorAtributoResource,
)
from plataforma_de_servicos.users.services import Permission


class InventarioSaldoInline(TabularInline):
    model = InventarioSaldo
    extra = 0
    fields = ("inventario", "quantidade")
    readonly_fields = ("inventario", "quantidade")
    can_delete = False
    verbose_name_plural = "Saldo por Inventário"

    def has_add_permission(self, request, obj=None):
        return False


class VariacaoProdutoInlineFormSet(BaseInlineFormSet):
    """Formset customizado que valida a soma do estoque das variações e a seleção de atributos."""

    def clean(self):
        super().clean()

        if not self.instance or not self.instance.pk:
            return

        # Validação de estoque
        produto_estoque = self.instance.estoque or 0
        if produto_estoque > 0:
            total_variacao_estoque = 0
            for form in self.forms:
                if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                    estoque = form.cleaned_data.get("estoque", 0) or 0
                    total_variacao_estoque += estoque

            if total_variacao_estoque > produto_estoque:
                raise forms.ValidationError(
                    f"O estoque total das variações ({total_variacao_estoque}) "
                    f"não pode exceder o estoque do produto ({produto_estoque}).",
                )

        # Validação de múltipla seleção por atributo
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                valores = form.cleaned_data.get("valores", [])
                if valores:
                    self._validar_selecao_atributos(valores, form)

    def _validar_selecao_atributos(self, valores, form):
        """Valida que atributos com multipla_selecao=False tenham apenas um valor."""
        from collections import defaultdict

        # Agrupar valores por atributo
        valores_por_atributo = defaultdict(list)
        for valor in valores:
            atributo = valor.atributo
            valores_por_atributo[atributo].append(valor)

        # Verificar cada atributo
        erros = []
        for atributo, vals in valores_por_atributo.items():
            if not atributo.multipla_selecao and len(vals) > 1:
                valores_str = ", ".join(v.valor for v in vals)
                erros.append(
                    f'O atributo "{atributo.nome}" permite apenas uma seleção, '
                    f'mas foram selecionados: {valores_str}'
                )

        if erros:
            raise forms.ValidationError(erros)


class ValorAtributoGerenteForm(forms.ModelForm):
    """Formulário com validação de exclusividade para modificadores de preço."""

    class Meta:
        model = ValorAtributo
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        preco = cleaned_data.get("preco_adicional") or 0
        percentual = cleaned_data.get("percentual_adicional") or 0

        if preco > 0 and percentual > 0:
            raise forms.ValidationError(
                "Escolha apenas uma opção: preço adicional OU percentual adicional, não ambos.",
            )
        return cleaned_data


class ImageInline(TabularInline):
    model = Image
    extra = 0
    verbose_name = "Imagem"
    verbose_name_plural = "Imagens"
    show_change_link = True

    readonly_fields = ["order"]


class VariacaoProdutoInline(TenantAwareInlineMixin, TabularInline):
    model = VariacaoProduto
    formset = VariacaoProdutoInlineFormSet
    extra = 0
    readonly_fields = ("sku", "preco_final_calculado", "estoque")
    fields = ("valores", "preco", "estoque", "preco_final_calculado", "sku")
    verbose_name = "Variação"
    verbose_name_plural = "Variações do Produto"

    class Media:
        css = {
            "all": ("css/valores-atributo-widget.css",),
        }
        js = ("js/valores-atributo-widget.js",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "valores":
            qs = ValorAtributo.objects.select_related("atributo", "atributo__categoria").order_by(
                "atributo__nome", "valor",
            )

            # Filtra valores pela categoria do produto sendo editado
            # O parent_obj é o Produto
            parent_obj = getattr(self, "parent_obj", None)
            categoria_id = None
            atributos_config = {}

            if parent_obj and hasattr(parent_obj, "categoria") and parent_obj.categoria:
                qs = qs.filter(atributo__categoria=parent_obj.categoria)
                categoria_id = parent_obj.categoria.pk

                # Buscar configuração de multipla_selecao de cada atributo
                atributos = Atributo.objects.filter(categoria=parent_obj.categoria)
                atributos_config = {
                    attr.nome: attr.multipla_selecao for attr in atributos
                }
            elif request.tenant:
                # Fallback: filtra pela empresa
                qs = qs.filter(atributo__categoria__empresa=request.tenant)

            kwargs["queryset"] = qs
            # Usa widget de checkboxes agrupados por atributo, passando a categoria
            kwargs["widget"] = GroupedCheckboxSelectMultiple(
                categoria_id=categoria_id,
                admin_site="gerentes",
                atributos_config=atributos_config,
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        """Armazena o objeto pai para uso no formfield_for_manytomany."""
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)

    @admin.display(description="Atributos Selecionados")
    def valores_display(self, obj):
        """Mostra os atributos selecionados com seus modificadores de preço."""
        if not obj.pk:
            return "-"
        partes = []
        for valor in obj.valores.select_related("atributo").all():
            texto = f"{valor.atributo.nome}: {valor.valor}"
            if valor.preco_adicional and valor.preco_adicional > 0:
                texto += f" (+R$ {valor.preco_adicional:,.2f})".replace(",", "X").replace(".", ",").replace("X", ".")
            elif valor.percentual_adicional and valor.percentual_adicional > 0:
                texto += f" (+{valor.percentual_adicional}%)"
            partes.append(texto)
        return " | ".join(partes) if partes else "-"

    @admin.display(description="Preço Final Calculado")
    def preco_final_calculado(self, obj):
        """Calcula o preço final baseado no preço base + modificadores."""
        if obj.pk:
            preco_final = obj.calcular_preco_final()
            return f"R$ {preco_final:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return "-"


class ProdutoGerenteAdmin(RBACAdminMixin, TenantAwareAdminMixin, ImportExportModelAdmin, ModelAdmin):
    # RBAC: Permissões por papel
    permission_view = Permission.PRODUTO_VISUALIZAR
    permission_add = Permission.PRODUTO_CRIAR
    permission_change = Permission.PRODUTO_EDITAR
    permission_delete = Permission.PRODUTO_DELETAR
    # Vendedores não podem ver/editar estes campos
    vendedor_readonly_fields = ["estoque_minimo"]

    # Import/Export configuration
    resource_classes = [TenantAwareProdutoResource]
    import_form_class = ImportForm
    export_form_class = ExportForm

    def get_resource_kwargs(self, request, *args, **kwargs):
        """Passa a empresa do tenant para o Resource."""
        kwargs = super().get_resource_kwargs(request, *args, **kwargs)
        kwargs["empresa"] = getattr(request, "tenant", None)
        return kwargs

    list_display = ["produto", "preco", "categoria", "count_variations"]
    list_display_links = ["produto"]
    list_per_page = 30
    list_select_related = ["categoria"]
    list_order_by = ["produto"]
    list_search = ["produto", "categoria__categoria"]
    search_fields = ["produto"]
    fieldsets = [
        (
            "Informações Básicas",
            {
                "fields": [
                    "produto",
                    "descricao",
                    "categoria",
                ],
                "description": "Dados principais do produto que aparecem na listagem e página de detalhe.",
            },
        ),
        (
            "Preço Base",
            {
                "fields": [
                    "preco",
                ],
                "description": "Este é o preço base do produto. As variações podem ter preços diferentes ou usar modificadores (valor fixo ou percentual) definidos nos atributos.",
            },
        ),
        (
            "Controle de Estoque",
            {
                "fields": [
                    "estoque_display",
                    "estoque_variacoes_display",
                    "estoque_disponivel_display",
                ],
                "description": (
                    "O estoque total do produto é gerenciado pelo sistema de movimentações de estoque (Entrada/Saída). "
                    "A soma do estoque de todas as variações não pode exceder o estoque total do produto."
                ),
            },
        ),
        (
            "Dados Fiscais e Estoque Mínimo",
            {
                "fields": [
                    "importado",
                    "ncm",
                    "estoque_minimo",
                    "data",
                ],
                "classes": ["collapse"],
                "description": "Informações fiscais e controle de estoque mínimo.",
            },
        ),
    ]
    inlines = [InventarioSaldoInline, ImageInline, VariacaoProdutoInline]
    readonly_fields = ["data", "estoque_display", "estoque_variacoes_display", "estoque_disponivel_display"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related("variacoes")
        return queryset

    @admin.display(description="Variações")
    def count_variations(self, obj):
        return obj.variacoes.count()

    @admin.display(description="Estoque Total do Produto")
    def estoque_display(self, obj):
        """Mostra o estoque total do produto (gerenciado via movimentações)."""
        if obj.pk:
            estoque = obj.estoque or 0
            if estoque == 0:
                return "Não definido (sem limite para variações)"
            return str(estoque)
        return "-"

    @admin.display(description="Estoque Alocado nas Variações")
    def estoque_variacoes_display(self, obj):
        """Mostra a soma do estoque de todas as variações."""
        if obj.pk:
            total = sum(v.estoque or 0 for v in obj.variacoes.all())
            return str(total)
        return "-"

    @admin.display(description="Estoque Disponível para Alocar")
    def estoque_disponivel_display(self, obj):
        """Mostra quanto estoque ainda pode ser alocado nas variações."""
        if obj.pk:
            estoque_produto = obj.estoque or 0
            if estoque_produto == 0:
                return "Sem limite definido"
            total_variacoes = sum(v.estoque or 0 for v in obj.variacoes.all())
            disponivel = estoque_produto - total_variacoes
            if disponivel < 0:
                return f"{disponivel} (EXCEDIDO!)"
            return str(disponivel)
        return "-"

    # Manter outras configurações do ModelAdmin
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True
    list_fullwidth = True
    list_horizontal_scrollbar_top = True
    list_disable_select_all = True
    actions_list = []
    actions_row = []
    actions_detail = []
    actions_submit_line = []
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        ArrayField: {
            "widget": ArrayWidget,
        },
    }


class ProdutoInline(TabularInline):
    model = Produto
    extra = 0
    verbose_name = "Produto"
    verbose_name_plural = "Produtos"
    show_change_link = True
    fieldsets = [
        (
            "Produto",
            {
                "fields": [
                    "produto",
                    "importado",
                    "ncm",
                    "estoque_minimo",
                    "data",
                ],
            },
        ),
        (
            "Categoria",
            {
                "fields": [
                    "categoria",
                ],
            },
        ),
    ]
    readonly_fields = ["produto", "data", "ncm", "importado"]


class CategoriaGerenteAdmin(RBACAdminMixin, TenantAwareAdminMixin, ImportExportModelAdmin, ModelAdmin):
    # RBAC: Permissões por papel
    permission_view = Permission.CATEGORIA_VISUALIZAR
    permission_add = Permission.CATEGORIA_CRIAR
    permission_change = Permission.CATEGORIA_EDITAR
    permission_delete = Permission.CATEGORIA_DELETAR

    # Import/Export configuration
    resource_classes = [CategoriaResource]
    import_form_class = ImportForm
    export_form_class = ExportForm

    list_display = ["categoria"]
    list_order_by = ["categoria"]
    list_order_by_desc = ["-categoria"]

    list_search = ["categoria"]
    list_search_fields = ["categoria"]

    search_fields = ["categoria"]

    inlines = [ProdutoInline]

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    list_horizontal_scrollbar_top = True
    list_disable_select_all = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


class ValorAtributoGerenteInline(TabularInline):
    model = ValorAtributo
    form = ValorAtributoGerenteForm
    extra = 1
    fields = ["valor", "preco_adicional", "percentual_adicional"]
    verbose_name = "Valor do Atributo"
    verbose_name_plural = "Valores do Atributo (escolha preço OU percentual, não ambos)"


class AtributoGerenteAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
    # RBAC: Usa mesmas permissões de produto (atributos são configuração de produto)
    permission_view = Permission.PRODUTO_VISUALIZAR
    permission_add = Permission.PRODUTO_CRIAR
    permission_change = Permission.PRODUTO_EDITAR
    permission_delete = Permission.PRODUTO_DELETAR

    list_display = ["nome", "categoria", "multipla_selecao_display", "count_valores"]
    list_filter = ["categoria", "multipla_selecao"]
    search_fields = ["nome", "categoria__categoria"]
    list_order_by = ["categoria", "nome"]
    list_select_related = ["categoria"]
    autocomplete_fields = ["categoria"]
    inlines = [ValorAtributoGerenteInline]
    compressed_fields = True
    warn_unsaved_form = True
    fieldsets = [
        (
            "Atributo",
            {
                "fields": ["categoria", "nome", "multipla_selecao"],
                "description": (
                    "Atributos são características do produto (ex: Cor, Tamanho, Sabor). "
                    "Cada atributo pertence a uma categoria específica. "
                    "Abaixo você pode adicionar os valores possíveis para este atributo."
                ),
            },
        ),
    ]

    @admin.display(description="Seleção", boolean=True)
    def multipla_selecao_display(self, obj):
        return obj.multipla_selecao

    def get_queryset(self, request):
        """Filtra atributos pela empresa via categoria."""
        qs = super(ModelAdmin, self).get_queryset(request)
        qs = qs.select_related("categoria", "categoria__empresa")
        tenant = getattr(request, "tenant", None)
        if self._is_gerente_admin():
            if not tenant:
                return qs.none()
            return qs.filter(categoria__empresa=tenant)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra categorias pela empresa do tenant."""
        if db_field.name == "categoria":
            tenant = getattr(request, "tenant", None)
            if tenant:
                from plataforma_de_servicos.produto.models import Categoria
                kwargs["queryset"] = Categoria.objects.filter(empresa=tenant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        """Pre-fill categoria from URL parameter when coming from product context."""
        initial = super().get_changeform_initial_data(request)
        categoria_id = request.GET.get("_categoria")
        if categoria_id:
            initial["categoria"] = categoria_id
        return initial

    def get_form(self, request, obj=None, **kwargs):
        """Hide categoria field when it's pre-filled from product context."""
        form = super().get_form(request, obj, **kwargs)
        categoria_id = request.GET.get("_categoria")
        # Only hide on add (not edit) and when _categoria is in URL
        if categoria_id and not obj:
            if "categoria" in form.base_fields:
                form.base_fields["categoria"].widget = forms.HiddenInput()
                form.base_fields["categoria"].required = False
        return form

    @admin.display(description="Valores Cadastrados")
    def count_valores(self, obj):
        return obj.valores.count()


class ValorAtributoGerenteAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
    # RBAC: Usa mesmas permissões de produto
    permission_view = Permission.PRODUTO_VISUALIZAR
    permission_add = Permission.PRODUTO_CRIAR
    permission_change = Permission.PRODUTO_EDITAR
    permission_delete = Permission.PRODUTO_DELETAR

    form = ValorAtributoGerenteForm
    list_display = ["atributo", "valor", "categoria_display", "modificador_display"]
    list_filter = ["atributo__categoria", "atributo"]
    search_fields = ["valor", "atributo__nome", "atributo__categoria__categoria"]
    autocomplete_fields = ["atributo"]
    list_select_related = ["atributo", "atributo__categoria"]
    list_order_by = ["atributo__categoria", "atributo__nome", "valor"]
    compressed_fields = True
    warn_unsaved_form = True
    fieldsets = [
        ("Identificação", {
            "fields": ["atributo", "valor"],
            "description": "Selecione o atributo (ex: Cor) e digite o valor (ex: Vermelho).",
        }),
        ("Modificador de Preço (escolha apenas um)", {
            "fields": ["preco_adicional", "percentual_adicional"],
            "description": (
                "Quando o cliente selecionar este valor, o preço será ajustado. Exemplos:\n"
                "- Preço adicional de R$ 5,00: produto de R$ 30 vira R$ 35\n"
                "- Percentual de 10%: produto de R$ 30 vira R$ 33\n\n"
                "IMPORTANTE: Use apenas UM dos campos (preço OU percentual)."
            ),
        }),
    ]

    def get_queryset(self, request):
        """Filtra valores de atributo pela empresa via categoria."""
        qs = super(ModelAdmin, self).get_queryset(request)
        qs = qs.select_related("atributo", "atributo__categoria", "atributo__categoria__empresa")
        tenant = getattr(request, "tenant", None)
        if self._is_gerente_admin():
            if not tenant:
                return qs.none()
            return qs.filter(atributo__categoria__empresa=tenant)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra atributos pela empresa e categoria do produto."""
        if db_field.name == "atributo":
            tenant = getattr(request, "tenant", None)
            categoria_id = request.GET.get("_categoria")

            qs = Atributo.objects.select_related("categoria")

            # Filtra pela categoria se fornecida via URL (contexto de produto)
            if categoria_id:
                qs = qs.filter(categoria_id=categoria_id)
            elif tenant:
                # Fallback: filtra apenas pela empresa
                qs = qs.filter(categoria__empresa=tenant)

            kwargs["queryset"] = qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def add_view(self, request, form_url="", extra_context=None):
        """Passa parâmetro _categoria para o template de adicionar atributo."""
        extra_context = extra_context or {}
        categoria_id = request.GET.get("_categoria")
        if categoria_id:
            extra_context["_categoria"] = categoria_id
        return super().add_view(request, form_url, extra_context)

    @admin.display(description="Categoria")
    def categoria_display(self, obj):
        """Mostra a categoria do atributo."""
        if obj.atributo and obj.atributo.categoria:
            return obj.atributo.categoria.categoria
        return "-"

    @admin.display(description="Modificador")
    def modificador_display(self, obj):
        """Mostra o modificador de preço de forma legível."""
        if obj.preco_adicional and obj.preco_adicional > 0:
            return f"+R$ {obj.preco_adicional:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if obj.percentual_adicional and obj.percentual_adicional > 0:
            return f"+{obj.percentual_adicional}%"
        return "-"

class VariacaoProdutoGerenteAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
    """Admin para VariacaoProduto com visual moderno Unfold e Busca Avançada."""
    
    # --- Lógica de Permissões e Tenant (Mantida) ---
    permission_view = Permission.VARIACAO_VISUALIZAR
    permission_add = Permission.VARIACAO_CRIAR
    permission_change = Permission.VARIACAO_EDITAR
    permission_delete = Permission.VARIACAO_DELETAR

    # --- Configurações Visuais Unfold ---
    list_fullwidth = True
    list_filter_sheet = True      
    list_filter_submit = True     
    compressed_fields = True
    warn_unsaved_form = True

    # --- BUSCA AVANÇADA (O que você solicitou) ---
    # Ao definir search_fields, o Unfold 2.0+ automaticamente usa o textarea expansível.
    search_fields = ["sku", "produto__produto", "valores__valor"]
    
    # Este texto aparece como ajuda e habilita a percepção de "Query Language" no UI
    search_help_text = _("Pesquisa avançada: Use termos específicos ou combine palavras-chave para filtrar SKUs, Produtos ou Atributos.")

    # --- Listagem Estilo 'Driver' ---
    list_display = [
        "display_identificacao", 
        "display_estoque_status", 
        "preco_final_display",
        "produto__categoria"
    ]
    
    list_filter = ["produto__categoria", "valores__atributo"]
    autocomplete_fields = ["produto"]
    list_select_related = ["produto"]

    # --- Quick Filters (Tabs) ---
    def get_tabs(self, request):
        """Abas superiores para filtragem rápida de estoque."""
        return [
            {
                "title": _("Todas"),
                "link": "./",
                "is_active": not request.GET.get("estoque"),
            },
            {
                "title": _("Em Estoque"),
                "link": "?estoque=disponivel",
                "is_active": request.GET.get("estoque") == "disponivel",
            },
            {
                "title": _("Estoque Baixo"),
                "link": "?estoque=baixo",
                "is_active": request.GET.get("estoque") == "baixo",
            },
        ]

    # --- Colunas Decoradas ---
    @display(description=_("Produto / SKU"), header=True)
    def display_identificacao(self, obj):
        return [
            obj.produto.produto,
            f"SKU: {obj.sku}",
        ]

    @display(
        description=_("Estoque"),
        label={
            "ALTA": "success",
            "BAIXA": "warning",
            "ZERO": "danger",
        },
    )
    def display_estoque_status(self, obj):
        if obj.estoque > 10: return "ALTA"
        if obj.estoque > 0: return "BAIXA"
        return "ZERO"

    @display(description=_("Preço Final"))
    def preco_final_display(self, obj):
        if obj.pk:
            preco = obj.calcular_preco_final()
            return f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return "-"

    # --- Ações de Linha ---
    actions_row = ["duplicar_variacao"]

    @action(description=_("Duplicar"), icon="content_copy")
    def duplicar_variacao(self, modeladmin, request, queryset):
        pass

    # --- Lógica de Queryset ---
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("produto").prefetch_related("valores", "valores__atributo")
        
        estoque_filter = request.GET.get("estoque")
        if estoque_filter == "disponivel":
            qs = qs.filter(estoque__gt=10)
        elif estoque_filter == "baixo":
            qs = qs.filter(estoque__gt=0, estoque__lte=10)
        elif estoque_filter == "zerado":
            qs = qs.filter(estoque=0)

        tenant = getattr(request, "tenant", None)
        if self._is_gerente_admin():
            if not tenant: return qs.none()
            return qs.filter(produto__empresa=tenant)
        return qs

    # (Manter get_form, formfield_for_manytomany e Media como no seu original)

# class VariacaoProdutoGerenteAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
#     """Admin para VariacaoProduto - usado principalmente para autocomplete no Estoque."""
#     # RBAC: Usa mesmas permissões de variação
#     permission_view = Permission.VARIACAO_VISUALIZAR
#     permission_add = Permission.VARIACAO_CRIAR
#     permission_change = Permission.VARIACAO_EDITAR
#     permission_delete = Permission.VARIACAO_DELETAR

#     list_display = ["produto", "sku", "estoque", "preco_final_display"]
#     list_filter = ["produto__categoria", "valores__atributo"]
#     search_fields = ["sku", "produto__produto", "valores__valor"]
#     autocomplete_fields = ["produto"]  # valores usa widget customizado
#     list_select_related = ["produto"]
#     list_order_by = ["produto__produto", "sku"]
#     readonly_fields = ["sku", "estoque"]  # estoque é gerenciado apenas via entradas/saídas
#     compressed_fields = True
#     warn_unsaved_form = True

#     fieldsets = [
#         (
#             "Produto",
#             {
#                 "fields": ["produto"],
#                 "description": "Selecione o produto para esta variação.",
#             },
#         ),
#         (
#             "Atributos da Variação",
#             {
#                 "fields": ["valores"],
#                 "description": "Selecione os valores dos atributos que definem esta variação (ex: Cor, Tamanho).",
#             },
#         ),
#         (
#             "Preço",
#             {
#                 "fields": ["preco"],
#                 "description": "Preço específico desta variação. Se vazio, usa o preço base do produto.",
#             },
#         ),
#         (
#             "Informações do Sistema",
#             {
#                 "fields": ["sku", "estoque"],
#                 "description": "Campos gerenciados automaticamente pelo sistema.",
#             },
#         ),
#     ]

#     class Media:
#         css = {
#             "all": ("css/valores-atributo-widget.css",),
#         }
#         js = ("js/valores-atributo-widget.js", "js/variacao-produto-form.js")

#     def get_queryset(self, request):
#         """Filtra variações pela empresa do tenant."""
#         qs = super().get_queryset(request).select_related(
#             "produto",
#         ).prefetch_related("valores", "valores__atributo")

#         tenant = getattr(request, "tenant", None)

#         # No admin de gerentes, sempre filtra por tenant
#         if self._is_gerente_admin():
#             if not tenant:
#                 return qs.none()  # Segurança: sem tenant, sem dados
#             return qs.filter(produto__empresa=tenant)

#         # No admin principal, superusuário sem tenant vê tudo
#         if request.user.is_superuser and not tenant:
#             return qs

#         # Para outros casos (ex: superuser com tenant), filtra
#         if tenant:
#             return qs.filter(produto__empresa=tenant)

#         # Fallback seguro para não vazar dados
#         return qs.none()

#     def formfield_for_manytomany(self, db_field, request, **kwargs):
#         """Usa widget de checkboxes agrupados para valores."""
#         if db_field.name == "valores":
#             tenant = getattr(request, "tenant", None)
#             obj = getattr(self, "_current_obj", None)

#             qs = ValorAtributo.objects.select_related("atributo", "atributo__categoria").order_by(
#                 "atributo__nome", "valor",
#             )

#             categoria_id = None
#             atributos_config = {}

#             # Se editando, filtra pela categoria do produto
#             if obj and obj.produto and obj.produto.categoria:
#                 categoria = obj.produto.categoria
#                 qs = qs.filter(atributo__categoria=categoria)
#                 categoria_id = categoria.pk
#                 atributos_config = {
#                     attr.nome: attr.multipla_selecao
#                     for attr in Atributo.objects.filter(categoria=categoria)
#                 }
#             elif tenant:
#                 # Fallback: filtra pela empresa
#                 qs = qs.filter(atributo__categoria__empresa=tenant)

#             kwargs["queryset"] = qs
#             kwargs["widget"] = GroupedCheckboxSelectMultiple(
#                 categoria_id=categoria_id,
#                 admin_site="gerentes",
#                 atributos_config=atributos_config,
#             )
#         return super().formfield_for_manytomany(db_field, request, **kwargs)

#     def get_form(self, request, obj=None, **kwargs):
#         """Armazena o objeto atual para uso no formfield_for_manytomany."""
#         self._current_obj = obj
#         return super().get_form(request, obj, **kwargs)

#     @admin.display(description="Preço Final")
#     def preco_final_display(self, obj):
#         """Mostra o preço final calculado."""
#         if obj.pk:
#             preco = obj.calcular_preco_final()
#             return f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
#         return "-"
