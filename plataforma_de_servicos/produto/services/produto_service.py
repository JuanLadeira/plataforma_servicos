from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import QuerySet

from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto

if TYPE_CHECKING:
    from plataforma_de_servicos.produto.models import VariacaoProduto


class ProdutoServiceError(Exception):
    """Exceção base para erros do serviço de Produto."""


@dataclass
class ProdutoVitrine:
    """Representação de um produto para exibição na vitrine."""

    id: int
    produto: str
    imagem: str | None
    slug: str
    categoria: str
    preco: Decimal | None
    estoque: int
    url: str


@dataclass
class VariacaoPrecoResult:
    """Resultado do cálculo de preço de uma variação."""

    preco: str
    preco_formatado: str
    estoque: int
    variation_id: int | None
    disponivel: bool
    combinacao_invalida: bool = False


class ProdutoService:
    """Serviço para gerenciar operações de Produto."""

    @staticmethod
    def _get_produtos_em_vitrine_subquery() -> Exists:
        """
        Retorna subquery para verificar se produto tem saldo em inventário exibível.

        Returns:
            Exists: Subquery para usar em annotate
        """
        return Exists(
            InventarioSaldo.objects.filter(
                produto=OuterRef("pk"),
                quantidade__gt=0,
                inventario__is_ativo=True,
                inventario__exibir_na_vitrine=True,
            ),
        )

    @staticmethod
    def listar_produtos_vitrine(
        category_id: int | str | None = None,
        search: str | None = None,
    ) -> tuple[QuerySet[Produto], Categoria | str]:
        """
        Lista produtos disponíveis na vitrine com filtros opcionais.

        Args:
            category_id: ID da categoria para filtrar (opcional)
            search: Texto para busca no nome do produto (opcional)

        Returns:
            tuple: (QuerySet de produtos, categoria selecionada ou string)
        """
        produtos_em_vitrine = ProdutoService._get_produtos_em_vitrine_subquery()
        categoria: Categoria | str = "Todos os produtos"

        if category_id:
            try:
                category_id_int = int(category_id)
                produtos = (
                    Produto.objects.filter(categoria__id=category_id_int)
                    .annotate(em_vitrine=produtos_em_vitrine)
                    .filter(em_vitrine=True)
                    .prefetch_related("images")
                )
                cat_obj = Categoria.objects.filter(id=category_id_int).first()
                if cat_obj:
                    categoria = cat_obj
            except (ValueError, TypeError):
                produtos = (
                    Produto.objects.annotate(em_vitrine=produtos_em_vitrine)
                    .filter(em_vitrine=True)
                    .prefetch_related("images")
                )
        else:
            produtos = (
                Produto.objects.annotate(em_vitrine=produtos_em_vitrine)
                .filter(em_vitrine=True)
                .prefetch_related("images")
            )

        if search:
            produtos = produtos.filter(produto__icontains=search)

        return produtos, categoria

    @staticmethod
    def preparar_produtos_para_vitrine(produtos: QuerySet[Produto]) -> list[ProdutoVitrine]:
        """
        Prepara lista de produtos para exibição na vitrine.

        Args:
            produtos: QuerySet de produtos

        Returns:
            list: Lista de ProdutoVitrine com estoque > 0
        """
        return [
            ProdutoVitrine(
                id=produto.id,
                produto=produto.produto,
                imagem=produto.get_image(),
                slug=produto.slug,
                categoria=produto.categoria.categoria if produto.categoria else "Sem categoria",
                preco=produto.preco,
                estoque=produto.estoque,
                url=produto.get_absolute_url(),
            )
            for produto in produtos
            if produto.estoque > 0
        ]

    @staticmethod
    def obter_atributos_variacoes(produto: Produto) -> list[dict]:
        """
        Obtém atributos únicos das variações de um produto.

        Args:
            produto: Produto para extrair atributos

        Returns:
            list: Lista de dicionários com atributo e seus valores
        """
        variacoes = produto.variacoes.prefetch_related("valores__atributo").all()

        atributos_dict: dict = {}
        for variacao in variacoes:
            for valor in variacao.valores.all():
                atributo = valor.atributo
                if atributo.id not in atributos_dict:
                    atributos_dict[atributo.id] = {
                        "atributo": atributo,
                        "valores": set(),
                    }
                atributos_dict[atributo.id]["valores"].add(valor)

        return [
            {
                "atributo": data["atributo"],
                "valores": sorted(data["valores"], key=lambda v: v.valor),
            }
            for data in atributos_dict.values()
        ]

    @staticmethod
    def _formatar_preco_br(preco: Decimal | None) -> str:
        """
        Formata preço no padrão brasileiro.

        Args:
            preco: Valor decimal do preço

        Returns:
            str: Preço formatado (ex: R$ 1.234,56)
        """
        if preco is None:
            return "R$ 0,00"
        return f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def buscar_variacao_por_valores(
        produto: Produto,
        valores_ids: list[str],
    ) -> VariacaoProduto | None:
        """
        Busca variação que corresponde exatamente aos valores selecionados.

        Args:
            produto: Produto para buscar variações
            valores_ids: Lista de IDs dos valores de atributo selecionados

        Returns:
            VariacaoProduto ou None se não encontrar correspondência exata
        """
        variacoes = produto.variacoes.prefetch_related("valores").all()
        valores_ids_set = set(map(int, valores_ids))

        for variacao in variacoes:
            variacao_valores_ids = set(variacao.valores.values_list("id", flat=True))
            if variacao_valores_ids == valores_ids_set:
                return variacao

        return None

    @staticmethod
    def calcular_preco_variacao(
        produto: Produto,
        valores_ids: list[str] | None = None,
    ) -> VariacaoPrecoResult:
        """
        Calcula preço de uma variação baseado nos valores selecionados.

        Args:
            produto: Produto base
            valores_ids: Lista de IDs dos valores de atributo (opcional)

        Returns:
            VariacaoPrecoResult: Resultado com preço, estoque e disponibilidade
        """
        if not valores_ids:
            return VariacaoPrecoResult(
                preco=str(produto.preco) if produto.preco else "0",
                preco_formatado=ProdutoService._formatar_preco_br(produto.preco),
                estoque=produto.estoque or 0,
                variation_id=None,
                disponivel=(produto.estoque or 0) > 0,
            )

        variacao = ProdutoService.buscar_variacao_por_valores(produto, valores_ids)

        if variacao:
            preco_final = variacao.calcular_preco_final()
            return VariacaoPrecoResult(
                preco=str(preco_final),
                preco_formatado=ProdutoService._formatar_preco_br(preco_final),
                estoque=variacao.estoque,
                variation_id=variacao.id,
                disponivel=variacao.estoque > 0,
            )

        return VariacaoPrecoResult(
            preco=str(produto.preco) if produto.preco else "0",
            preco_formatado=ProdutoService._formatar_preco_br(produto.preco),
            estoque=produto.estoque or 0,
            variation_id=None,
            disponivel=(produto.estoque or 0) > 0,
            combinacao_invalida=True,
        )
