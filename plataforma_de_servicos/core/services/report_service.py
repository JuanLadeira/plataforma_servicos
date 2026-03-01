"""
Report Service - Serviço de relatórios pré-definidos.

Fornece templates de relatórios comuns para o sistema,
utilizando os serviços de exportação para gerar arquivos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from django.db.models import Avg
from django.db.models import Count
from django.db.models import F
from django.db.models import Sum
from django.http import HttpResponse

from plataforma_de_servicos.core.services.export_service import ExcelExportService
from plataforma_de_servicos.core.services.export_service import ExportColumn
from plataforma_de_servicos.core.services.export_service import ExportConfig
from plataforma_de_servicos.core.services.export_service import PDFExportService

if TYPE_CHECKING:
    from plataforma_de_servicos.empresa.models import Empresa


class ReportFormat(Enum):
    """Formatos de exportação disponíveis."""
    EXCEL = "excel"
    PDF = "pdf"


class ReportType(Enum):
    """Tipos de relatórios disponíveis."""
    INVENTORY_STOCK = "inventory_stock"
    INVENTORY_MOVEMENT = "inventory_movement"
    INVENTORY_TURNOVER = "inventory_turnover"
    INVENTORY_VALUATION = "inventory_valuation"
    INVENTORY_RUPTURE = "inventory_rupture"
    ORDER_SUMMARY = "order_summary"
    COMMISSION_REPORT = "commission_report"


@dataclass
class ReportResult:
    """Resultado de um relatório."""
    success: bool
    message: str
    response: HttpResponse | None = None
    preview_html: str | None = None


class ReportService:
    """
    Serviço para geração de relatórios.

    Centraliza a criação de relatórios pré-definidos,
    aplicando as configurações corretas para cada tipo.
    """

    def __init__(self, empresa: "Empresa"):
        self.empresa = empresa

    def generate(
        self,
        report_type: ReportType,
        format: ReportFormat = ReportFormat.EXCEL,
        filters: dict | None = None,
        preview: bool = False,
    ) -> ReportResult:
        """
        Gera um relatório do tipo especificado.

        Args:
            report_type: Tipo do relatório
            format: Formato de saída (Excel ou PDF)
            filters: Filtros adicionais a aplicar
            preview: Se True, retorna HTML para preview ao invés de arquivo

        Returns:
            ReportResult com o arquivo ou preview
        """
        filters = filters or {}

        # Mapear tipo de relatório para método gerador
        report_generators = {
            ReportType.INVENTORY_STOCK: self._generate_inventory_stock,
            ReportType.INVENTORY_MOVEMENT: self._generate_inventory_movement,
            ReportType.INVENTORY_TURNOVER: self._generate_inventory_turnover,
            ReportType.INVENTORY_VALUATION: self._generate_inventory_valuation,
            ReportType.INVENTORY_RUPTURE: self._generate_inventory_rupture,
            ReportType.ORDER_SUMMARY: self._generate_order_summary,
            ReportType.COMMISSION_REPORT: self._generate_commission_report,
        }

        generator = report_generators.get(report_type)
        if not generator:
            return ReportResult(
                success=False,
                message=f"Tipo de relatório não suportado: {report_type}",
            )

        try:
            return generator(format, filters, preview)
        except Exception as e:
            return ReportResult(
                success=False,
                message=f"Erro ao gerar relatório: {str(e)}",
            )

    def _generate_inventory_stock(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório de saldo de estoque."""
        from plataforma_de_servicos.inventario.models import InventarioSaldo

        queryset = (
            InventarioSaldo.objects
            .filter(inventario__empresa=self.empresa)
            .select_related("produto", "variacao", "inventario")
            .order_by("inventario__nome", "produto__produto")
        )

        # Aplicar filtros
        if filters.get("inventario_id"):
            queryset = queryset.filter(inventario_id=filters["inventario_id"])
        if filters.get("categoria_id"):
            queryset = queryset.filter(produto__categoria_id=filters["categoria_id"])
        if filters.get("estoque_minimo"):
            queryset = queryset.filter(quantidade__lte=filters["estoque_minimo"])

        config = ExportConfig(
            filename="relatorio_estoque",
            title="Relatório de Saldo de Estoque",
            subtitle=f"Período: {datetime.now().strftime('%d/%m/%Y')}",
            company_name=self.empresa.nome,
            columns=[
                ExportColumn("inventario__nome", "Inventário", width=20),
                ExportColumn("produto__produto", "Produto", width=30),
                ExportColumn(
                    lambda s: s.variacao.get_nome_completo() if s.variacao else "-",
                    "Variação",
                    width=25,
                ),
                ExportColumn("quantidade", "Quantidade", width=12, align="right"),
                ExportColumn("atualizado_em", "Última Atualização", width=18),
            ],
        )

        return self._export_with_format(queryset, config, format, preview)

    def _generate_inventory_movement(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório de movimentação de estoque."""
        from plataforma_de_servicos.estoque.models import Estoque

        queryset = (
            Estoque.objects
            .filter(empresa=self.empresa)
            .select_related("funcionario__usuario", "inventario_origem", "inventario_destino")
            .prefetch_related("itens__produto", "itens__variacao")
            .order_by("-created")
        )

        # Aplicar filtros de data
        if filters.get("data_inicio"):
            queryset = queryset.filter(created__gte=filters["data_inicio"])
        if filters.get("data_fim"):
            queryset = queryset.filter(created__lte=filters["data_fim"])
        if filters.get("movimento"):
            queryset = queryset.filter(movimento=filters["movimento"])

        config = ExportConfig(
            filename="relatorio_movimentacao",
            title="Relatório de Movimentação de Estoque",
            subtitle=self._format_date_range(filters.get("data_inicio"), filters.get("data_fim")),
            company_name=self.empresa.nome,
            page_orientation="landscape",
            columns=[
                ExportColumn("created", "Data/Hora", width=18),
                ExportColumn("get_movimento_display", "Tipo", width=15),
                ExportColumn("inventario_origem__nome", "Origem", width=20),
                ExportColumn("inventario_destino__nome", "Destino", width=20),
                ExportColumn("funcionario__usuario__name", "Responsável", width=20),
                ExportColumn(
                    lambda e: e.itens.count(),
                    "Qtd. Itens",
                    width=10,
                    align="right",
                ),
                ExportColumn("observacao", "Observação", width=30),
            ],
        )

        return self._export_with_format(queryset, config, format, preview)

    def _generate_inventory_turnover(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório de giro de estoque."""
        from plataforma_de_servicos.estoque.models import EstoqueItens
        from plataforma_de_servicos.inventario.models import InventarioSaldo

        # Calcular giro por produto
        # Giro = Saídas no período / Saldo médio
        queryset = (
            EstoqueItens.objects
            .filter(
                estoque__empresa=self.empresa,
                estoque__movimento="S",  # Apenas saídas
            )
            .values("produto__produto", "produto_id")
            .annotate(
                total_saidas=Sum("quantidade"),
                qtd_movimentos=Count("id"),
            )
            .order_by("-total_saidas")
        )

        # Aplicar filtros de data
        if filters.get("data_inicio"):
            queryset = queryset.filter(estoque__created__gte=filters["data_inicio"])
        if filters.get("data_fim"):
            queryset = queryset.filter(estoque__created__lte=filters["data_fim"])

        config = ExportConfig(
            filename="relatorio_giro_estoque",
            title="Relatório de Giro de Estoque",
            subtitle=self._format_date_range(filters.get("data_inicio"), filters.get("data_fim")),
            company_name=self.empresa.nome,
            columns=[
                ExportColumn("produto__produto", "Produto", width=35),
                ExportColumn("total_saidas", "Total Saídas", width=15, align="right"),
                ExportColumn("qtd_movimentos", "Qtd. Movimentos", width=15, align="right"),
            ],
        )

        return self._export_with_format(queryset, config, format, preview)

    def _generate_inventory_valuation(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório de valorização de inventário."""
        from plataforma_de_servicos.inventario.models import InventarioSaldo

        queryset = (
            InventarioSaldo.objects
            .filter(
                inventario__empresa=self.empresa,
                quantidade__gt=0,
            )
            .select_related("produto", "variacao", "inventario")
            .annotate(
                preco_unitario=F("produto__preco"),
                valor_total=F("quantidade") * F("produto__preco"),
            )
            .order_by("-valor_total")
        )

        if filters.get("inventario_id"):
            queryset = queryset.filter(inventario_id=filters["inventario_id"])

        config = ExportConfig(
            filename="relatorio_valorizacao",
            title="Relatório de Valorização de Inventário",
            subtitle=f"Data: {datetime.now().strftime('%d/%m/%Y')}",
            company_name=self.empresa.nome,
            columns=[
                ExportColumn("inventario__nome", "Inventário", width=20),
                ExportColumn("produto__produto", "Produto", width=30),
                ExportColumn("quantidade", "Quantidade", width=12, align="right"),
                ExportColumn(
                    "preco_unitario",
                    "Preço Unit.",
                    width=15,
                    align="right",
                    format_func=lambda v: f"R$ {v:,.2f}" if v else "R$ 0,00",
                ),
                ExportColumn(
                    "valor_total",
                    "Valor Total",
                    width=15,
                    align="right",
                    format_func=lambda v: f"R$ {v:,.2f}" if v else "R$ 0,00",
                ),
            ],
            extra_data={
                "show_totals": True,
                "total_value": queryset.aggregate(total=Sum("valor_total"))["total"] or 0,
            },
        )

        return self._export_with_format(queryset, config, format, preview)

    def _generate_inventory_rupture(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório de ruptura de estoque (produtos zerados ou baixos)."""
        from plataforma_de_servicos.inventario.models import InventarioSaldo
        from plataforma_de_servicos.produto.models import Produto

        # Produtos com estoque zero ou abaixo do mínimo
        threshold = filters.get("estoque_minimo", 5)

        queryset = (
            InventarioSaldo.objects
            .filter(
                inventario__empresa=self.empresa,
                inventario__exibir_na_vitrine=True,
                quantidade__lte=threshold,
            )
            .select_related("produto", "variacao", "inventario")
            .order_by("quantidade", "produto__produto")
        )

        config = ExportConfig(
            filename="relatorio_ruptura",
            title="Relatório de Ruptura de Estoque",
            subtitle=f"Produtos com estoque <= {threshold} unidades",
            company_name=self.empresa.nome,
            columns=[
                ExportColumn("inventario__nome", "Inventário", width=20),
                ExportColumn("produto__produto", "Produto", width=30),
                ExportColumn(
                    lambda s: s.variacao.get_nome_completo() if s.variacao else "-",
                    "Variação",
                    width=25,
                ),
                ExportColumn(
                    "quantidade",
                    "Estoque Atual",
                    width=12,
                    align="right",
                ),
                ExportColumn(
                    lambda s: "ZERADO" if s.quantidade == 0 else "BAIXO",
                    "Status",
                    width=12,
                    align="center",
                ),
            ],
        )

        return self._export_with_format(queryset, config, format, preview)

    def _generate_order_summary(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório resumido de ordens de compra."""
        from plataforma_de_servicos.vendas.models import OrdemCompra

        queryset = (
            OrdemCompra.objects
            .filter(empresa=self.empresa)
            .select_related("interesse", "corretor__usuario")
            .order_by("-created")
        )

        # Filtros
        if filters.get("data_inicio"):
            queryset = queryset.filter(created__gte=filters["data_inicio"])
        if filters.get("data_fim"):
            queryset = queryset.filter(created__lte=filters["data_fim"])
        if filters.get("status"):
            queryset = queryset.filter(status=filters["status"])

        config = ExportConfig(
            filename="relatorio_ordens",
            title="Relatório de Ordens de Compra",
            subtitle=self._format_date_range(filters.get("data_inicio"), filters.get("data_fim")),
            company_name=self.empresa.nome,
            page_orientation="landscape",
            columns=[
                ExportColumn("numero", "Número", width=15),
                ExportColumn("created", "Data", width=18),
                ExportColumn("nome_cliente", "Cliente", width=25),
                ExportColumn("get_status_display", "Status", width=15),
                ExportColumn("valor_total", "Valor Total", width=15, align="right"),
                ExportColumn("corretor__usuario__name", "Vendedor", width=20),
            ],
        )

        return self._export_with_format(queryset, config, format, preview)

    def _generate_commission_report(
        self,
        format: ReportFormat,
        filters: dict,
        preview: bool,
    ) -> ReportResult:
        """Gera relatório de comissões."""
        from plataforma_de_servicos.vendas.models import Comissao

        queryset = (
            Comissao.objects
            .filter(empresa=self.empresa)
            .select_related("ordem", "funcionario__usuario")
            .order_by("-created")
        )

        # Filtros
        if filters.get("data_inicio"):
            queryset = queryset.filter(created__gte=filters["data_inicio"])
        if filters.get("data_fim"):
            queryset = queryset.filter(created__lte=filters["data_fim"])
        if filters.get("status"):
            queryset = queryset.filter(status=filters["status"])
        if filters.get("funcionario_id"):
            queryset = queryset.filter(funcionario_id=filters["funcionario_id"])

        config = ExportConfig(
            filename="relatorio_comissoes",
            title="Relatório de Comissões",
            subtitle=self._format_date_range(filters.get("data_inicio"), filters.get("data_fim")),
            company_name=self.empresa.nome,
            columns=[
                ExportColumn("ordem__numero", "Ordem", width=15),
                ExportColumn("funcionario__usuario__name", "Vendedor", width=25),
                ExportColumn("valor_base", "Valor Base", width=15, align="right"),
                ExportColumn("percentual", "Percentual", width=12, align="right"),
                ExportColumn("valor_comissao", "Valor Comissão", width=15, align="right"),
                ExportColumn("get_status_display", "Status", width=12),
            ],
            extra_data={
                "show_totals": True,
                "total_comissao": queryset.aggregate(total=Sum("valor_comissao"))["total"] or 0,
            },
        )

        return self._export_with_format(queryset, config, format, preview)

    def _export_with_format(
        self,
        queryset,
        config: ExportConfig,
        format: ReportFormat,
        preview: bool,
    ) -> ReportResult:
        """Executa exportação no formato especificado."""
        if format == ReportFormat.EXCEL:
            service = ExcelExportService(config)
            if preview:
                return ReportResult(
                    success=False,
                    message="Preview não disponível para Excel",
                )
            response = service.export(queryset)
        else:
            service = PDFExportService(config)
            if preview:
                html = service.preview_html(queryset)
                return ReportResult(
                    success=True,
                    message="Preview gerado com sucesso",
                    preview_html=html,
                )
            response = service.export(queryset)

        return ReportResult(
            success=True,
            message="Relatório gerado com sucesso",
            response=response,
        )

    def _format_date_range(self, start_date, end_date) -> str:
        """Formata intervalo de datas para exibição."""
        if start_date and end_date:
            return f"Período: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        elif start_date:
            return f"A partir de: {start_date.strftime('%d/%m/%Y')}"
        elif end_date:
            return f"Até: {end_date.strftime('%d/%m/%Y')}"
        return f"Data: {datetime.now().strftime('%d/%m/%Y')}"
