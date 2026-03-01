"""
ProductSearchService - Serviço centralizado para busca e filtragem de produtos.

Segue o padrão Model -> Service -> View, encapsulando toda a lógica
de busca, filtragem e contagem de produtos para a vitrine.
"""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import QuerySet

from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.produto.models.categoria_model import Categoria

if TYPE_CHECKING:
    from plataforma_de_servicos.empresa.models import Empresa


@dataclass
class SearchFilter:
    """Representa um filtro ativo de busca."""
    type: str  # 'category', 'search', 'price_range', etc.
    value: str
    label: str
    removable: bool = True


@dataclass
class CategoryCount:
    """Contagem de produtos por categoria."""
    id: int
    nome: str
    slug: str
    count: int


@dataclass
class PriceRange:
    """Faixa de preço dos resultados."""
    min_price: Decimal
    max_price: Decimal


@dataclass
class SearchResult:
    """Resultado completo de uma busca."""
    variations: QuerySet[VariacaoProduto]
    total_count: int
    category: Categoria | None
    category_name: str
    active_filters: list[SearchFilter]
    category_counts: list[CategoryCount]
    price_range: PriceRange | None = None


@dataclass
class SearchParams:
    """Parâmetros de busca."""
    category_id: int | str | None = None
    search_query: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    order_by: str = "-data"  # default: mais recentes
    page: int = 1
    page_size: int = 24


class ProductSearchService:
    """
    Serviço centralizado para busca e filtragem de produtos.

    Encapsula toda a lógica de:
    - Busca textual por nome e atributos
    - Filtragem por categoria
    - Filtragem por faixa de preço
    - Contagem de produtos por categoria (sincronizada com filtros)
    - Gerenciamento de filtros ativos
    """

    def __init__(self, empresa: "Empresa | None"):
        self.empresa = empresa

    def search(self, params: SearchParams) -> SearchResult:
        """
        Executa uma busca com os parâmetros fornecidos.

        Args:
            params: Parâmetros de busca

        Returns:
            SearchResult com variações, contagens e filtros ativos
        """
        if not self.empresa:
            return SearchResult(
                variations=VariacaoProduto.objects.none(),
                total_count=0,
                category=None,
                category_name="Todos os produtos",
                active_filters=[],
                category_counts=[],
            )

        # Base queryset com filtro de vitrine
        base_qs = self._get_vitrine_queryset()

        # Aplicar filtros
        filtered_qs = base_qs
        active_filters: list[SearchFilter] = []
        category: Categoria | None = None

        # Filtro por categoria
        if params.category_id:
            filtered_qs, category = self._apply_category_filter(
                filtered_qs, params.category_id
            )
            if category:
                active_filters.append(SearchFilter(
                    type="category",
                    value=str(category.id),
                    label=f"Categoria: {category.categoria}",
                ))

        # Filtro de busca textual
        if params.search_query:
            filtered_qs = self._apply_search_filter(filtered_qs, params.search_query)
            active_filters.append(SearchFilter(
                type="search",
                value=params.search_query,
                label=f"Busca: {params.search_query}",
            ))

        # Filtro de preço
        if params.min_price or params.max_price:
            filtered_qs = self._apply_price_filter(
                filtered_qs, params.min_price, params.max_price
            )
            price_label = self._format_price_filter_label(
                params.min_price, params.max_price
            )
            active_filters.append(SearchFilter(
                type="price",
                value=f"{params.min_price or 0}-{params.max_price or 'max'}",
                label=price_label,
            ))

        # Ordenação
        filtered_qs = self._apply_ordering(filtered_qs, params.order_by)

        # Contagem total
        total_count = filtered_qs.count()

        # Contagem por categoria (baseada nos filtros atuais, exceto categoria)
        category_counts = self._get_category_counts(
            base_qs if not params.search_query else self._apply_search_filter(base_qs, params.search_query),
            exclude_category_id=params.category_id,
        )

        # Faixa de preço dos resultados
        price_range = self._get_price_range(filtered_qs)

        return SearchResult(
            variations=filtered_qs,
            total_count=total_count,
            category=category,
            category_name=category.categoria if category else "Todos os produtos",
            active_filters=active_filters,
            category_counts=category_counts,
            price_range=price_range,
        )

    def get_suggestions(self, query: str, limit: int = 5) -> list[str]:
        """
        Retorna sugestões de busca baseadas no texto digitado.

        Args:
            query: Texto parcial da busca
            limit: Número máximo de sugestões

        Returns:
            Lista de sugestões de busca
        """
        if not self.empresa or len(query) < 2:
            return []

        # Busca em nomes de produtos
        produto_suggestions = (
            VariacaoProduto.objects
            .filter(
                produto__empresa=self.empresa,
                produto__disponivel=True,
                produto__produto__icontains=query,
            )
            .values_list("produto__produto", flat=True)
            .distinct()[:limit]
        )

        # Busca em valores de atributos
        atributo_suggestions = (
            VariacaoProduto.objects
            .filter(
                produto__empresa=self.empresa,
                produto__disponivel=True,
                valores__valor__icontains=query,
            )
            .values_list("valores__valor", flat=True)
            .distinct()[:limit]
        )

        # Combinar e limitar
        suggestions = list(set(produto_suggestions) | set(atributo_suggestions))
        return sorted(suggestions)[:limit]

    def _get_vitrine_queryset(self) -> QuerySet[VariacaoProduto]:
        """Retorna queryset base filtrado para vitrine."""
        inventario_vitrine_subquery = InventarioSaldo.objects.filter(
            produto=OuterRef("produto"),
            inventario__exibir_na_vitrine=True,
            inventario__is_ativo=True,
            quantidade__gt=0,
        )

        return (
            VariacaoProduto.objects
            .filter(
                produto__disponivel=True,
                produto__empresa=self.empresa,
                estoque__gt=0,
            )
            .annotate(tem_saldo_vitrine=Exists(inventario_vitrine_subquery))
            .filter(tem_saldo_vitrine=True)
            .select_related("produto", "produto__categoria")
            .prefetch_related("valores__atributo")
        )

    def _apply_category_filter(
        self,
        qs: QuerySet[VariacaoProduto],
        category_id: int | str,
    ) -> tuple[QuerySet[VariacaoProduto], Categoria | None]:
        """Aplica filtro de categoria."""
        try:
            category_id_int = int(category_id)
            filtered = qs.filter(produto__categoria__id=category_id_int)
            category = Categoria.objects.filter(
                id=category_id_int,
                empresa=self.empresa,
            ).first()
            return filtered, category
        except (ValueError, TypeError):
            return qs, None

    def _apply_search_filter(
        self,
        qs: QuerySet[VariacaoProduto],
        search_query: str,
    ) -> QuerySet[VariacaoProduto]:
        """Aplica filtro de busca textual."""
        return qs.filter(
            Q(produto__produto__icontains=search_query) |
            Q(valores__valor__icontains=search_query) |
            Q(produto__descricao__icontains=search_query)
        ).distinct()

    def _apply_price_filter(
        self,
        qs: QuerySet[VariacaoProduto],
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> QuerySet[VariacaoProduto]:
        """Aplica filtro de faixa de preço."""
        if min_price:
            qs = qs.filter(produto__preco__gte=min_price)
        if max_price:
            qs = qs.filter(produto__preco__lte=max_price)
        return qs

    def _apply_ordering(
        self,
        qs: QuerySet[VariacaoProduto],
        order_by: str,
    ) -> QuerySet[VariacaoProduto]:
        """Aplica ordenação."""
        order_mapping = {
            "price_asc": "produto__preco",
            "price_desc": "-produto__preco",
            "name_asc": "produto__produto",
            "name_desc": "-produto__produto",
            "-data": "-produto__data",
            "data": "produto__data",
        }
        order_field = order_mapping.get(order_by, "-produto__data")
        return qs.order_by(order_field)

    def _get_category_counts(
        self,
        base_qs: QuerySet[VariacaoProduto],
        exclude_category_id: int | str | None = None,
    ) -> list[CategoryCount]:
        """
        Calcula contagem de produtos por categoria.

        A contagem respeita os filtros ativos (exceto categoria),
        permitindo que o usuário veja quantos produtos existem
        em cada categoria com os filtros de busca aplicados.
        """
        # Agrupar por categoria e contar
        category_counts = (
            base_qs
            .values("produto__categoria__id", "produto__categoria__categoria", "produto__categoria__slug")
            .annotate(count=Count("id"))
            .filter(count__gt=0)
            .order_by("produto__categoria__categoria")
        )

        return [
            CategoryCount(
                id=item["produto__categoria__id"],
                nome=item["produto__categoria__categoria"],
                slug=item["produto__categoria__slug"],
                count=item["count"],
            )
            for item in category_counts
            if item["produto__categoria__id"] is not None
        ]

    def _get_price_range(
        self,
        qs: QuerySet[VariacaoProduto],
    ) -> PriceRange | None:
        """Calcula faixa de preço dos resultados."""
        from django.db.models import Max, Min

        result = qs.aggregate(
            min_price=Min("produto__preco"),
            max_price=Max("produto__preco"),
        )

        if result["min_price"] and result["max_price"]:
            return PriceRange(
                min_price=result["min_price"],
                max_price=result["max_price"],
            )
        return None

    def _format_price_filter_label(
        self,
        min_price: Decimal | None,
        max_price: Decimal | None,
    ) -> str:
        """Formata label para filtro de preço."""
        if min_price and max_price:
            return f"Preço: R$ {min_price:.2f} - R$ {max_price:.2f}"
        elif min_price:
            return f"Preço: acima de R$ {min_price:.2f}"
        elif max_price:
            return f"Preço: até R$ {max_price:.2f}"
        return "Preço: filtrado"
