
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Q, Sum

from .models import Categoria, Produto, VariacaoProduto
from plataforma_de_servicos.inventario.models import InventarioSaldo

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('categoria', 'slug')
    search_fields = ('categoria',)
    prepopulated_fields = {'slug': ('categoria',)}

class VariacaoProdutoInline(admin.TabularInline):
    model = VariacaoProduto
    extra = 1
    autocomplete_fields = ('valores',)
    readonly_fields = ('estoque',)  # estoque é gerenciado apenas via entradas/saídas

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'categoria', 'disponivel', 'estoque')
    list_filter = ('disponivel', 'categoria')
    search_fields = ('produto', 'descricao')
    prepopulated_fields = {'slug': ('produto',)}
    readonly_fields = ('estoque',)  # estoque é gerenciado apenas via entradas/saídas
    inlines = [VariacaoProdutoInline]
    change_list_template = 'admin/produto/produto_changelist.html'

    # 1. Adicionar a URL para o relatório
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'report-hidden-products/',
                self.admin_site.admin_view(self.view_hidden_products_report),
                name='report_hidden_products',
            ),
        ]
        return custom_urls + urls

    # 2. Adicionar a view que gera o relatório
    def view_hidden_products_report(self, request):
        # Lógica para encontrar produtos não exibidos
        
        # Variações com estoque zero
        variacoes_sem_estoque = VariacaoProduto.objects.filter(estoque__lte=0)

        # Variações em inventários não-vitrine
        saldos_em_inventario_oculto = InventarioSaldo.objects.filter(
            quantidade__gt=0,
            inventario__exibir_na_vitrine=False
        )
        variacoes_em_inventario_oculto = VariacaoProduto.objects.filter(
            id__in=saldos_em_inventario_oculto.values_list('variacao_id', flat=True)
        )

        # Produtos simples (sem variações) com estoque zero
        produtos_simples_sem_estoque = Produto.objects.filter(
            variacoes__isnull=True,
            estoque__lte=0
        )

        context = dict(
           self.admin_site.each_context(request),
           variacoes_sem_estoque=variacoes_sem_estoque,
           variacoes_em_inventario_oculto=variacoes_em_inventario_oculto,
           produtos_simples_sem_estoque=produtos_simples_sem_estoque,
        )
        return render(request, 'admin/produto/report_hidden_products.html', context)

    # 3. Adicionar o botão na lista de produtos
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['report_url'] = 'report-hidden-products/'
        return super().changelist_view(request, extra_context=extra_context)
