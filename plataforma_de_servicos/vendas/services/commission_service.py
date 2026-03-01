"""
CommissionService - Serviço para gerenciamento de comissões.

Segue o padrão Model -> Service -> View, encapsulando toda a lógica de negócio
relacionada a cálculo, criação e atualização de comissões de vendedores.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from plataforma_de_servicos.vendas.models.comissao import Comissao
from plataforma_de_servicos.vendas.models.comissao import ComissaoCategoria
from plataforma_de_servicos.vendas.models.comissao import ComissaoVendedor
from plataforma_de_servicos.vendas.models.comissao import ConfiguracaoComissao
from plataforma_de_servicos.vendas.models.comissao import StatusComissao

if TYPE_CHECKING:
    from plataforma_de_servicos.empresa.models import Empresa
    from plataforma_de_servicos.users.models import Funcionario
    from plataforma_de_servicos.vendas.models import OrdemCompra


class CommissionServiceError(Exception):
    """Exceção base para erros do serviço de comissões."""


@dataclass
class CommissionCalculation:
    """Resultado do cálculo de comissão."""
    percentual: Decimal
    valor_base: Decimal
    valor_comissao: Decimal
    fonte_percentual: str  # 'vendedor', 'categoria', 'padrao'
    detalhes: str


@dataclass
class CommissionResult:
    """Resultado de uma operação de comissão."""
    success: bool
    message: str
    comissao: Comissao | None = None


class CommissionService:
    """
    Serviço para gerenciamento de comissões de vendedores.

    Responsabilidades:
    - Obter percentual de comissão (vendedor > categoria > padrão)
    - Calcular valor da comissão
    - Criar comissões ao aprovar ordens
    - Recalcular comissões quando percentual é alterado
    - Gerenciar fluxo de aprovação e pagamento
    """

    def __init__(self, empresa: "Empresa"):
        self.empresa = empresa
        self._config: ConfiguracaoComissao | None = None

    @property
    def config(self) -> ConfiguracaoComissao | None:
        """Obtém ou cria configuração de comissão da empresa."""
        if self._config is None:
            self._config = ConfiguracaoComissao.objects.filter(
                empresa=self.empresa
            ).first()
        return self._config

    def obter_percentual(
        self,
        funcionario: "Funcionario",
        categoria_id: int | None = None,
    ) -> tuple[Decimal, str]:
        """
        Obtém o percentual de comissão aplicável.

        Hierarquia de prioridade:
        1. Percentual específico do vendedor
        2. Percentual da categoria do produto
        3. Percentual padrão da empresa

        Args:
            funcionario: Vendedor para obter percentual
            categoria_id: ID da categoria do produto (opcional)

        Returns:
            Tupla com (percentual, fonte) onde fonte indica a origem
        """
        if not self.config:
            return Decimal("0.00"), "sem_configuracao"

        # 1. Verificar percentual específico do vendedor
        comissao_vendedor = ComissaoVendedor.objects.filter(
            configuracao=self.config,
            funcionario=funcionario,
        ).first()

        if comissao_vendedor:
            return comissao_vendedor.percentual, "vendedor"

        # 2. Verificar percentual por categoria
        if categoria_id:
            comissao_categoria = ComissaoCategoria.objects.filter(
                configuracao=self.config,
                categoria_id=categoria_id,
            ).first()

            if comissao_categoria:
                return comissao_categoria.percentual, "categoria"

        # 3. Retornar percentual padrão
        return self.config.percentual_padrao, "padrao"

    def calcular_comissao(
        self,
        ordem: "OrdemCompra",
        funcionario: "Funcionario",
    ) -> CommissionCalculation:
        """
        Calcula a comissão para uma ordem de compra.

        Args:
            ordem: Ordem de compra
            funcionario: Vendedor responsável

        Returns:
            CommissionCalculation com detalhes do cálculo
        """
        # Determinar valor base
        valor_base = ordem.valor_total

        # Obter categoria predominante da ordem (primeira categoria encontrada)
        categoria_id = None
        primeiro_item = ordem.itens.select_related("produto__categoria").first()
        if primeiro_item and primeiro_item.produto and primeiro_item.produto.categoria:
            categoria_id = primeiro_item.produto.categoria_id

        # Obter percentual
        percentual, fonte = self.obter_percentual(funcionario, categoria_id)

        # Calcular valor
        valor_comissao = (valor_base * percentual / Decimal("100")).quantize(
            Decimal("0.01")
        )

        # Montar detalhes
        detalhes_map = {
            "vendedor": f"Percentual específico do vendedor: {percentual}%",
            "categoria": f"Percentual da categoria: {percentual}%",
            "padrao": f"Percentual padrão da empresa: {percentual}%",
            "sem_configuracao": "Empresa sem configuração de comissão",
        }

        return CommissionCalculation(
            percentual=percentual,
            valor_base=valor_base,
            valor_comissao=valor_comissao,
            fonte_percentual=fonte,
            detalhes=detalhes_map.get(fonte, ""),
        )

    @transaction.atomic
    def criar_comissao(
        self,
        ordem: "OrdemCompra",
        funcionario: "Funcionario | None" = None,
    ) -> CommissionResult:
        """
        Cria comissão para uma ordem de compra.

        Args:
            ordem: Ordem de compra aprovada
            funcionario: Vendedor (usa corretor da ordem se não informado)

        Returns:
            CommissionResult com resultado da operação
        """
        # Usar corretor da ordem se não informado
        if funcionario is None:
            funcionario = ordem.corretor

        if funcionario is None:
            return CommissionResult(
                success=False,
                message="Ordem não possui vendedor/corretor vinculado.",
            )

        # Verificar se já existe comissão
        comissao_existente = Comissao.objects.filter(
            ordem=ordem,
            funcionario=funcionario,
        ).first()

        if comissao_existente:
            return CommissionResult(
                success=False,
                message=f"Já existe comissão para esta ordem e vendedor.",
                comissao=comissao_existente,
            )

        # Calcular comissão
        calculo = self.calcular_comissao(ordem, funcionario)

        if calculo.percentual <= 0:
            return CommissionResult(
                success=False,
                message="Percentual de comissão é zero ou não configurado.",
            )

        # Criar comissão
        comissao = Comissao.objects.create(
            empresa=self.empresa,
            ordem=ordem,
            funcionario=funcionario,
            percentual=calculo.percentual,
            valor_base=calculo.valor_base,
            valor_comissao=calculo.valor_comissao,
            status=StatusComissao.PENDENTE,
            observacoes=calculo.detalhes,
        )

        return CommissionResult(
            success=True,
            message=f"Comissão de R$ {calculo.valor_comissao:.2f} criada com sucesso.",
            comissao=comissao,
        )

    @transaction.atomic
    def recalcular_comissao(
        self,
        comissao: Comissao,
        novo_percentual: Decimal | None = None,
    ) -> CommissionResult:
        """
        Recalcula uma comissão existente.

        Só permite recalcular se a comissão estiver pendente.

        Args:
            comissao: Comissão a recalcular
            novo_percentual: Novo percentual (opcional, mantém atual se não informado)

        Returns:
            CommissionResult com resultado da operação
        """
        if comissao.status != StatusComissao.PENDENTE:
            return CommissionResult(
                success=False,
                message="Só é possível recalcular comissões pendentes.",
                comissao=comissao,
            )

        # Atualizar percentual se informado
        if novo_percentual is not None:
            comissao.percentual = novo_percentual

        # Recalcular valor
        comissao.valor_comissao = comissao.calcular_valor()
        comissao.save()

        return CommissionResult(
            success=True,
            message=f"Comissão recalculada: R$ {comissao.valor_comissao:.2f}",
            comissao=comissao,
        )

    @transaction.atomic
    def aprovar_comissao(self, comissao: Comissao) -> CommissionResult:
        """
        Aprova uma comissão para pagamento.

        Args:
            comissao: Comissão a aprovar

        Returns:
            CommissionResult com resultado da operação
        """
        if not comissao.pode_aprovar:
            return CommissionResult(
                success=False,
                message=f"Comissão não pode ser aprovada. Status atual: {comissao.status}",
                comissao=comissao,
            )

        comissao.status = StatusComissao.APROVADA
        comissao.data_aprovacao = timezone.now().date()
        comissao.save()

        return CommissionResult(
            success=True,
            message="Comissão aprovada com sucesso.",
            comissao=comissao,
        )

    @transaction.atomic
    def pagar_comissao(self, comissao: Comissao) -> CommissionResult:
        """
        Marca uma comissão como paga.

        Args:
            comissao: Comissão a marcar como paga

        Returns:
            CommissionResult com resultado da operação
        """
        if not comissao.pode_pagar:
            return CommissionResult(
                success=False,
                message=f"Comissão não pode ser paga. Status atual: {comissao.status}",
                comissao=comissao,
            )

        comissao.status = StatusComissao.PAGA
        comissao.data_pagamento = timezone.now().date()
        comissao.save()

        return CommissionResult(
            success=True,
            message="Comissão marcada como paga.",
            comissao=comissao,
        )

    @transaction.atomic
    def cancelar_comissao(
        self,
        comissao: Comissao,
        motivo: str = "",
    ) -> CommissionResult:
        """
        Cancela uma comissão.

        Args:
            comissao: Comissão a cancelar
            motivo: Motivo do cancelamento (opcional)

        Returns:
            CommissionResult com resultado da operação
        """
        if not comissao.pode_cancelar:
            return CommissionResult(
                success=False,
                message=f"Comissão não pode ser cancelada. Status atual: {comissao.status}",
                comissao=comissao,
            )

        comissao.status = StatusComissao.CANCELADA
        if motivo:
            comissao.observacoes = f"{comissao.observacoes}\nCancelamento: {motivo}".strip()
        comissao.save()

        return CommissionResult(
            success=True,
            message="Comissão cancelada.",
            comissao=comissao,
        )

    def listar_comissoes_pendentes(self) -> list[Comissao]:
        """Retorna comissões pendentes da empresa."""
        return list(
            Comissao.objects.filter(
                empresa=self.empresa,
                status=StatusComissao.PENDENTE,
            ).select_related("ordem", "funcionario__usuario")
        )

    def resumo_comissoes(
        self,
        funcionario: "Funcionario | None" = None,
        data_inicio=None,
        data_fim=None,
    ) -> dict:
        """
        Retorna resumo de comissões.

        Args:
            funcionario: Filtrar por vendedor (opcional)
            data_inicio: Data inicial (opcional)
            data_fim: Data final (opcional)

        Returns:
            Dict com totais por status
        """
        from django.db.models import Count, Sum

        queryset = Comissao.objects.filter(empresa=self.empresa)

        if funcionario:
            queryset = queryset.filter(funcionario=funcionario)
        if data_inicio:
            queryset = queryset.filter(created__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(created__lte=data_fim)

        # Agrupar por status
        resumo = queryset.values("status").annotate(
            total_valor=Sum("valor_comissao"),
            quantidade=Count("id"),
        )

        result = {
            "total_geral": Decimal("0.00"),
            "quantidade_total": 0,
            "por_status": {},
        }

        for item in resumo:
            status = item["status"]
            result["por_status"][status] = {
                "valor": item["total_valor"] or Decimal("0.00"),
                "quantidade": item["quantidade"],
            }
            result["total_geral"] += item["total_valor"] or Decimal("0.00")
            result["quantidade_total"] += item["quantidade"]

        return result
