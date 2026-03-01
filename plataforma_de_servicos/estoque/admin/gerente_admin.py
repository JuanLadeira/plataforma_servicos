from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.core.admin.mixins import RBACAdminMixin
from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.users.services import Permission
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto


class ProdutoFilter(SimpleListFilter):
    """Filtro para listar estoques que contêm itens de um produto específico."""

    title = _("Produto")
    parameter_name = "produto"

    def lookups(self, request, model_admin):
        # Retorna lista vazia - o filtro será usado via URL apenas
        return []

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(estoque_itens__produto__id=self.value()).distinct()
        return queryset

    def has_output(self):
        # Não mostrar no sidebar, mas ainda processar o parâmetro
        return False


class EstoqueItensForm(forms.ModelForm):
    """Formulário customizado que preenche o produto automaticamente a partir da variação."""

    class Meta:
        model = EstoqueItens
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        variacao = cleaned_data.get("variacao")

        # Se tem variação, preenche o produto automaticamente
        if variacao:
            cleaned_data["produto"] = variacao.produto

        return cleaned_data

    def save(self, commit=True):
        """Garante que o produto seja definido a partir da variação antes de salvar."""
        instance = super().save(commit=False)

        # Se tem variação, define o produto
        if instance.variacao and not instance.produto_id:
            instance.produto = instance.variacao.produto

        if commit:
            instance.save()

        return instance


class EstoqueItensInline(TabularInline):
    model = EstoqueItens
    form = EstoqueItensForm
    extra = 1
    autocomplete_fields = ("variacao",)

    class Media:
        css = {
            "all": ("css/estoque-itens-widget.css",),
        }
        js = ("js/estoque-itens-widget.js",)

    def get_fields(self, request, obj=None):
        """
        Campos diferentes para criação vs edição:
        - Criação: variacao, quantidade, saldo_atual (API), saldo_preview (calculado JS)
        - Edição: variacao, quantidade, saldo_anterior, saldo (fotografia histórica)
        """
        if obj and obj.pk:
            # Modo edição - mostra fotografia histórica
            return ("variacao", "quantidade", "saldo_anterior", "saldo")
        # Modo criação - mostra preview dinâmico
        return ("variacao", "quantidade", "saldo_atual", "saldo_preview")

    def get_readonly_fields(self, request, obj=None):
        """Se estoque já existe (edição), todos os campos são readonly."""
        if obj and obj.pk:
            return ("variacao", "quantidade", "saldo_anterior", "saldo")
        return ("saldo_atual", "saldo_preview")

    def has_add_permission(self, request, obj=None):
        """Não permite adicionar itens em estoque já criado."""
        if obj and obj.pk:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar itens em estoque já criado."""
        if obj and obj.pk:
            return False
        return True

    @admin.display(description="Saldo Atual")
    def saldo_atual(self, obj):
        """Mostra o saldo atual da variação (preenchido via JS/API)."""
        # Este campo será atualizado via JavaScript
        return "-"

    @admin.display(description="Saldo Após")
    def saldo_preview(self, obj):
        """Mostra o preview do saldo após a operação (calculado via JS)."""
        # Este campo será atualizado via JavaScript
        return "-"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        tenant = getattr(request, "tenant", None)
        if db_field.name == "variacao":
            qs = VariacaoProduto.objects.select_related(
                "produto", "produto__categoria",
            ).prefetch_related("valores", "valores__atributo")
            if tenant:
                qs = qs.filter(produto__empresa=tenant)
            kwargs["queryset"] = qs
        elif db_field.name == "produto" and tenant:
            from plataforma_de_servicos.produto.models import Produto
            kwargs["queryset"] = Produto.objects.filter(empresa=tenant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TransferenciaEstoqueItensInline(TabularInline):
    model = EstoqueItens
    form = EstoqueItensForm
    extra = 1
    autocomplete_fields = ("variacao",)

    class Media:
        css = {
            "all": ("css/estoque-itens-widget.css",),
        }
        js = ("js/estoque-itens-widget.js",)

    def get_fields(self, request, obj=None):
        if obj and obj.pk:
            # Modo edição - mostra fotografia histórica
            return ("variacao", "quantidade", "saldo_anterior", "saldo")
        # Modo criação - mostra preview dinâmico
        return ("variacao", "quantidade", "saldo_atual", "saldo_preview")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            return ("variacao", "quantidade", "saldo_anterior", "saldo")
        return ("saldo_atual", "saldo_preview")

    def has_add_permission(self, request, obj=None):
        return not obj or not obj.pk

    def has_delete_permission(self, request, obj=None):
        return not obj or not obj.pk

    @admin.display(description="Saldo Atual")
    def saldo_atual(self, obj):
        """Mostra o saldo atual da variação (preenchido via JS/API)."""
        return "-"

    @admin.display(description="Saldo Após")
    def saldo_preview(self, obj):
        """Mostra o preview do saldo após a operação (calculado via JS)."""
        return "-"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        tenant = getattr(request, "tenant", None)
        if db_field.name == "variacao":
            qs = VariacaoProduto.objects.select_related(
                "produto", "produto__categoria",
            ).prefetch_related("valores", "valores__atributo")
            if tenant:
                qs = qs.filter(produto__empresa=tenant)
            kwargs["queryset"] = qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


def get_inventario(estoque):
    if estoque.movimento == Movimento.ENTRADA.value:
        return estoque.inventario_destino
    if estoque.movimento == Movimento.SAIDA.value:
        return estoque.inventario_origem
    if estoque.movimento == Movimento.TRANSFERENCIA.value:
        return estoque.inventario_destino
    return None


class EstoqueEntradaAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
    # RBAC: Permissões de estoque
    permission_view = Permission.ESTOQUE_VISUALIZAR
    permission_add = Permission.ESTOQUE_ENTRADA
    permission_change = Permission.ESTOQUE_ENTRADA

    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario", "data")
    search_fields = ("nf", "data")
    list_filter = ("funcionario", "inventario_destino", ProdutoFilter)
    change_form_template = "admin/estoque/change_form_observacoes_final.html"

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    list_horizontal_scrollbar_top = True
    list_disable_select_all = True

    actions_list = []  # Displayed above the results list
    actions_row = []  # Displayed in a table row in results list
    actions_detail = []  # Displayed at the top of for in object detail
    actions_submit_line = []  # Displayed near save in object detail

    fieldsets = [
        (
            "Informações da Entrada",
            {
                "fields": [
                    "inventario_destino",
                    "funcionario",
                    "nf",
                ],
                "description": "Dados básicos da entrada de estoque.",
            },
        ),
        (
            "Observações",
            {
                "fields": ["observacao"],
            },
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        """
        Se estoque já existe (edição), todos os campos são readonly,
        exceto 'nf' se estiver vazio.
        """
        if obj and obj.pk:
            readonly = ["inventario_destino", "funcionario", "observacao"]
            if obj.nf:
                readonly.append("nf")
            return readonly
        return ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "movimento" in form.base_fields:
            # Usar widget Hidden com valor explícito em vez de apenas initial
            form.base_fields["movimento"].widget = forms.HiddenInput()
            form.base_fields["movimento"].initial = Movimento.ENTRADA.value
            form.base_fields["movimento"].required = False
        if "processado" in form.base_fields:
            form.base_fields["processado"].widget = forms.HiddenInput()
        if "inventario_origem" in form.base_fields:
            form.base_fields["inventario_origem"].widget = forms.HiddenInput()
        # Campos específicos de saída - ocultar na entrada
        if "origem_saida" in form.base_fields:
            form.base_fields["origem_saida"].widget = forms.HiddenInput()
        if "ordem_compra" in form.base_fields:
            form.base_fields["ordem_compra"].widget = forms.HiddenInput()
        return form

    def save_model(self, request, obj, form, change):
        """Garante que movimento seja definido para entrada."""
        if not change:
            obj.movimento = Movimento.ENTRADA.value
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar entradas de estoque já processadas."""
        if obj and obj.pk:
            return False
        return True

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        """
        O método save_related é chamado após o salvamento
        do formulário principal e dos formulários inline.
        Só processa na criação (change=False), não na edição.
        """
        super().save_related(request, form, formsets, change)
        if not change:
            obj = form.instance
            obj.processar()

    def save_formset(self, request, form, formset, change):
        # Só processa na criação
        if not change:
            instances = formset.save(commit=False)
            entrada = form.instance

            inventario = get_inventario(entrada)

            if not inventario and instances:
                from django.contrib import messages
                messages.error(
                    request,
                    "Erro: É necessário selecionar um inventário de destino antes de adicionar itens.",
                )
                return

            for instance in instances:
                instance.inventario = inventario
                instance.save()
            formset.save_m2m()


class EstoqueSaidaAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
    # RBAC: Permissões de estoque
    permission_view = Permission.ESTOQUE_VISUALIZAR
    permission_add = Permission.ESTOQUE_SAIDA
    permission_change = Permission.ESTOQUE_SAIDA

    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario", "origem_saida", "ordem_compra")
    search_fields = ("nf",)
    list_filter = ("funcionario", "origem_saida", "inventario_origem", ProdutoFilter)
    change_form_template = "admin/estoque/change_form_observacoes_final.html"

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    list_horizontal_scrollbar_top = True
    list_disable_select_all = True

    actions_list = []  # Displayed above the results list
    actions_row = []  # Displayed in a table row in results list
    actions_detail = []  # Displayed at the top of for in object detail
    actions_submit_line = []  # Displayed near save in object detail

    def get_fieldsets(self, request, obj=None):
        """
        Retorna fieldsets dinamicamente:
        - Na criação: não exibe 'Informações do Sistema'
        - Na edição: exibe 'Informações do Sistema' apenas se ordem_compra tiver valor
        """
        fieldsets = [
            (
                "Informações da Saída",
                {
                    "fields": [
                        "inventario_origem",
                        "funcionario",
                        "nf",
                    ],
                    "description": "Dados básicos da saída de estoque.",
                },
            ),
            (
                "Detalhes da Saída",
                {
                    "fields": [
                        "origem_saida",
                    ],
                    "description": "Motivo da saída (opcional).",
                },
            ),
            (
                "Observações",
                {
                    "fields": ["observacao"],
                },
            ),
        ]

        # Na edição, se tiver ordem_compra, adiciona o fieldset de sistema
        if obj and obj.pk and obj.ordem_compra:
            fieldsets.insert(2, (
                "Informações do Sistema",
                {
                    "fields": ["ordem_compra"],
                    "description": "Campos preenchidos automaticamente pelo sistema.",
                },
            ))

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        """
        Se estoque já existe (edição), todos os campos são readonly,
        exceto 'nf' se estiver vazio (para permitir adicionar NF em saídas automáticas).
        """
        if obj and obj.pk:
            # Campos sempre readonly em edição
            readonly = ["inventario_origem", "funcionario", "origem_saida", "observacao", "ordem_compra"]
            # Se NF já tem valor, também é readonly
            if obj.nf:
                readonly.append("nf")
            return readonly
        return ("ordem_compra",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
            form.base_fields["movimento"].initial = Movimento.SAIDA.value
            form.base_fields["movimento"].required = False

        if "processado" in form.base_fields:
            form.base_fields["processado"].widget = forms.HiddenInput()

        if "inventario_destino" in form.base_fields:
            form.base_fields["inventario_destino"].widget = forms.HiddenInput()

        # Tornar origem_saida não obrigatório
        if "origem_saida" in form.base_fields:
            form.base_fields["origem_saida"].required = False

        return form

    def save_model(self, request, obj, form, change):
        """Garante que movimento seja definido para saída."""
        if not change:
            obj.movimento = Movimento.SAIDA.value
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar saídas de estoque já processadas."""
        if obj and obj.pk:
            return False
        return True

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        # Só processa na criação (change=False), não na edição
        if not change:
            obj = form.instance
            obj.processar()

    def save_formset(self, request, form, formset, change):
        # Só processa na criação
        if not change:
            instances = formset.save(commit=False)
            saida = form.instance

            inventario = get_inventario(saida)

            if not inventario and instances:
                from django.contrib import messages
                messages.error(
                    request,
                    "Erro: É necessário selecionar um inventário de origem antes de adicionar itens.",
                )
                return

            for instance in instances:
                instance.inventario = inventario
                instance.save()
            formset.save_m2m()


class TransferenciaAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
    # RBAC: Permissões de estoque
    permission_view = Permission.ESTOQUE_VISUALIZAR
    permission_add = Permission.ESTOQUE_TRANSFERENCIA
    permission_change = Permission.ESTOQUE_TRANSFERENCIA

    inlines = (TransferenciaEstoqueItensInline,)
    list_display = ("__str__", "funcionario", "inventario_origem", "inventario_destino", "data")
    search_fields = ("data",)
    list_filter = ("funcionario",)
    change_form_template = "admin/estoque/change_form_observacoes_final.html"

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

    fieldsets = [
        (
            "Informações da Transferência",
            {
                "fields": [
                    "inventario_origem",
                    "inventario_destino",
                    "funcionario",
                ],
                "description": "Dados da transferência entre inventários.",
            },
        ),
        (
            "Observações",
            {
                "fields": ["observacao"],
            },
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            return ["inventario_origem", "inventario_destino", "funcionario", "observacao"]
        return ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
            form.base_fields["movimento"].initial = Movimento.TRANSFERENCIA.value
            form.base_fields["movimento"].required = False
        if "nf" in form.base_fields:
            form.base_fields["nf"].widget = forms.HiddenInput()
        if "origem_saida" in form.base_fields:
            form.base_fields["origem_saida"].widget = forms.HiddenInput()
        if "processado" in form.base_fields:
            form.base_fields["processado"].widget = forms.HiddenInput()
        if "ordem_compra" in form.base_fields:
            form.base_fields["ordem_compra"].widget = forms.HiddenInput()
        return form

    def save_model(self, request, obj, form, change):
        """Garante que movimento seja definido para transferência."""
        if not change:
            obj.movimento = Movimento.TRANSFERENCIA.value
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.pk:
            return False
        return True

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        if not change:
            obj = form.instance
            obj.processar()

    def save_formset(self, request, form, formset, change):
        if not change:
            instances = formset.save(commit=False)
            transferencia = form.instance
            # Na transferência, os itens saem do inventário de origem
            inventario_origem = transferencia.inventario_origem

            if not inventario_origem and instances:
                from django.contrib import messages
                messages.error(
                    request,
                    "Erro: É necessário selecionar um inventário de origem antes de adicionar itens.",
                )
                return

            for instance in instances:
                instance.inventario = inventario_origem
                instance.save()
            formset.save_m2m()
