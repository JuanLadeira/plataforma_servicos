from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction

from plataforma_de_servicos.inventario.models import Inventario

from .choices.movimento import Movimento
from .choices.origem_saida import OrigemSaida
from .models import Estoque
from .models import EstoqueItens

if TYPE_CHECKING:
    from plataforma_de_servicos.vendas.models.ordem_compra import OrdemCompra

User = get_user_model()


class EstoqueService:
    """
    Serviço para gerenciar operações de estoque de forma consistente
    """

    @staticmethod
    def criar_saida_por_ordem_compra(ordem_compra: "OrdemCompra", itens_pedido: list, funcionario: User = None, inventario_origem: Inventario = None):
        """
        Cria uma saída de estoque para uma ordem de compra

        Args:
            ordem_compra: Ordem de compra que originou a saída
            itens_pedido: Lista de dicts com 'produto', 'quantidade', 'variacao' (opcional)
            funcionario: Usuário responsável pela operação
            inventario_origem: Depósito de origem, da mesma empresa da ordem (obrigatório)

        Returns:
            Estoque: Registro de saída criado

        Raises:
            ValueError: sem depósito ou com depósito de outra empresa
        """
        if inventario_origem is None:
            raise ValueError("inventario_origem é obrigatório")
        if inventario_origem.empresa_id != ordem_compra.empresa_id:
            raise ValueError("depósito de outra empresa")

        with transaction.atomic():
            # Criar registro de saída
            saida = Estoque.objects.create(
                empresa=ordem_compra.empresa,
                funcionario=funcionario,
                movimento=Movimento.SAIDA.value,
                origem_saida=OrigemSaida.PEDIDO.value,
                ordem_compra=ordem_compra,
                inventario_origem=inventario_origem,
                observacao=f"Saída automática para ordem de compra #{ordem_compra.pk}",
            )

            # Criar itens da saída
            for item in itens_pedido:
                EstoqueItens.objects.create(
                    estoque=saida,
                    produto=item["produto"],
                    variacao=item.get("variacao"),
                    quantidade=item["quantidade"],
                    inventario=inventario_origem,
                )

            # Processar a saída automaticamente
            saida.processar()

            return saida

    @staticmethod
    def criar_saida_manual(origem: str, itens: list, funcionario: User, inventario_origem: Inventario = None, observacao: str = ""):
        """
        Cria uma saída de estoque manual (perda, ajuste, etc.)

        Args:
            origem: Tipo de origem da saída (OrigemSaida)
            itens: Lista de dicts com 'produto', 'quantidade' e 'variacao' (opcional)
            funcionario: Usuário responsável
            inventario_origem: Depósito de origem (obrigatório); a saída fica na empresa dele
            observacao: Observações adicionais
        """
        if inventario_origem is None:
            raise ValueError("inventario_origem é obrigatório")

        with transaction.atomic():
            saida = Estoque.objects.create(
                empresa=inventario_origem.empresa,
                funcionario=funcionario,
                movimento=Movimento.SAIDA.value,
                origem_saida=origem,
                inventario_origem=inventario_origem,
                observacao=observacao,
            )

            for item in itens:
                EstoqueItens.objects.create(
                    estoque=saida,
                    produto=item["produto"],
                    variacao=item.get("variacao"),
                    quantidade=item["quantidade"],
                    inventario=inventario_origem,
                )

            return saida

    @staticmethod
    def liberar_reserva_para_saida(reservas_carrinho: list, ordem_compra: "OrdemCompra", funcionario: User = None):
        """
        Converte reservas do carrinho em saída efetiva de estoque

        Args:
            reservas_carrinho: Lista de reservas do carrinho
            ordem_compra: Ordem de compra gerada
            funcionario: Usuário (opcional)
        """

        itens_pedido = []

        for reserva in reservas_carrinho:
            if reserva.variacao_produto:
                produto = reserva.variacao_produto.produto
            else:
                produto = reserva.produto

            itens_pedido.append({
                "produto": produto,
                "quantidade": reserva.quantidade,
                "variacao": reserva.variacao_produto if reserva.variacao_produto else None,
            })

        return EstoqueService.criar_saida_por_ordem_compra(
            ordem_compra=ordem_compra,
            itens_pedido=itens_pedido,
            funcionario=funcionario,
            inventario_origem=Inventario.objects.padrao_da_empresa(ordem_compra.empresa),
        )
