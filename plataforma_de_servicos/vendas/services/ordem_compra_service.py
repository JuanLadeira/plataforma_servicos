from django.db import transaction
from django.utils import timezone

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.estoque.services import EstoqueService
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra


class OrdemCompraServiceError(Exception):
    """Exceção base para erros do serviço de OrdemCompra."""



class OrdemCompraService:
    """Serviço para gerenciar operações de OrdemCompra."""

    @staticmethod
    def gerar_numero() -> str:
        """
        Gera número único no formato OC-YYYY-NNNNN.

        Returns:
            str: Número da ordem (ex: OC-2026-00001)
        """
        ano = timezone.now().year
        prefixo = f"OC-{ano}-"

        ultima_ordem = (
            OrdemCompra.objects.filter(numero__startswith=prefixo)
            .order_by("-numero")
            .first()
        )

        if ultima_ordem:
            ultimo_numero = int(ultima_ordem.numero.split("-")[-1])
            novo_numero = ultimo_numero + 1
        else:
            novo_numero = 1

        return f"{prefixo}{novo_numero:05d}"

    @staticmethod
    @transaction.atomic
    def criar_ordem_de_interesse(interesse: InteresseCompra) -> OrdemCompra:
        """
        Cria OrdemCompra a partir de um InteresseCompra convertido.

        Args:
            interesse: InteresseCompra que foi convertido

        Returns:
            OrdemCompra: Ordem de compra criada

        Raises:
            OrdemCompraServiceError: Se o interesse não estiver convertido
                                     ou já tiver uma ordem associada
        """
        if interesse.status != StatusInteresse.CONVERTIDO:
            raise OrdemCompraServiceError(
                f"Interesse deve estar com status CONVERTIDO. Status atual: {interesse.status}",
            )

        if hasattr(interesse, "ordem_compra"):
            raise OrdemCompraServiceError(
                f"Interesse #{interesse.pk} já possui uma ordem de compra associada.",
            )

        # Criar a ordem
        ordem = OrdemCompra.objects.create(
            numero=OrdemCompraService.gerar_numero(),
            interesse=interesse,
            nome_cliente=interesse.nome_cliente,
            email_cliente=interesse.email_cliente,
            telefone_cliente=interesse.telefone_cliente,
            valor_total=interesse.valor_total,
            status=StatusOrdemCompra.PENDENTE_APROVACAO,
            corretor=interesse.corretor,
        )

        # Criar itens da ordem a partir dos itens do interesse
        for item_interesse in interesse.itens.all():
            ItemOrdemCompra.objects.create(
                ordem=ordem,
                produto=None,  # ItemInteresse não tem FK para Produto
                variacao=None,  # ItemInteresse não tem FK para VariacaoProduto
                produto_nome=item_interesse.produto_nome,
                variacao_info=item_interesse.variacao_info,
                quantidade=item_interesse.quantidade,
                preco_unitario=item_interesse.preco_unitario,
            )

        return ordem

    @staticmethod
    @transaction.atomic
    def aprovar(ordem: OrdemCompra, usuario: User) -> OrdemCompra:
        """
        Aprova a ordem de compra.

        Args:
            ordem: OrdemCompra a ser aprovada
            usuario: Usuário que está aprovando

        Returns:
            OrdemCompra: Ordem atualizada

        Raises:
            OrdemCompraServiceError: Se a ordem não puder ser aprovada
        """
        # 1. Validar primeiro
        if not ordem.pode_aprovar:
            raise OrdemCompraServiceError(
                f"Ordem {ordem.numero} não pode ser aprovada. Status atual: {ordem.status}",
                )

        # 2. Coletar itens e criar saída de estoque
        itens_pedido = []
        for item in ordem.itens.all():
            if item.produto:
                itens_pedido.append({
                    "produto": item.produto,
                    "variacao": item.variacao,
                    "quantidade": item.quantidade,
                })

        if itens_pedido:
            EstoqueService.criar_saida_por_pedido(
                pedido_id=ordem.pk,
                itens_pedido=itens_pedido,
                funcionario=usuario,
            )

        # 3. Atualizar o status da ordem
        ordem.status = StatusOrdemCompra.APROVADA
        ordem.aprovado_por = usuario
        ordem.data_aprovacao = timezone.now()
        ordem.save()

        return ordem

    @staticmethod
    @transaction.atomic
    def rejeitar(ordem: OrdemCompra, usuario: User, motivo: str) -> OrdemCompra:
        """
        Rejeita a ordem de compra.

        Args:
            ordem: OrdemCompra a ser rejeitada
            usuario: Usuário que está rejeitando
            motivo: Motivo da rejeição (obrigatório)

        Returns:
            OrdemCompra: Ordem atualizada

        Raises:
            OrdemCompraServiceError: Se a ordem não puder ser rejeitada
                                     ou se o motivo não for informado
        """
        if not ordem.pode_rejeitar:
            raise OrdemCompraServiceError(
                f"Ordem {ordem.numero} não pode ser rejeitada. Status atual: {ordem.status}",
            )

        if not motivo or not motivo.strip():
            raise OrdemCompraServiceError("É obrigatório informar o motivo da rejeição.")

        ordem.status = StatusOrdemCompra.REJEITADA
        ordem.aprovado_por = usuario
        ordem.data_aprovacao = timezone.now()
        ordem.motivo_rejeicao = motivo.strip()
        ordem.save()

        return ordem

    @staticmethod
    @transaction.atomic
    def faturar(ordem: OrdemCompra) -> OrdemCompra:
        """
        Marca a ordem como faturada (fatura emitida).

        Args:
            ordem: OrdemCompra a ser faturada

        Returns:
            OrdemCompra: Ordem atualizada

        Raises:
            OrdemCompraServiceError: Se a ordem não puder ser faturada
        """
        if not ordem.pode_faturar:
            raise OrdemCompraServiceError(
                f"Ordem {ordem.numero} não pode ser faturada. Status atual: {ordem.status}",
            )

        ordem.status = StatusOrdemCompra.FATURADA
        ordem.save()

        return ordem

    @staticmethod
    @transaction.atomic
    def cancelar(ordem: OrdemCompra, motivo: str = "") -> OrdemCompra:
        """
        Cancela a ordem de compra.

        Args:
            ordem: OrdemCompra a ser cancelada
            motivo: Motivo do cancelamento (opcional)

        Returns:
            OrdemCompra: Ordem atualizada

        Raises:
            OrdemCompraServiceError: Se a ordem não puder ser cancelada
        """
        if not ordem.pode_cancelar:
            raise OrdemCompraServiceError(
                f"Ordem {ordem.numero} não pode ser cancelada. Status atual: {ordem.status}",
            )

        ordem.status = StatusOrdemCompra.CANCELADA
        if motivo:
            ordem.observacoes = f"{ordem.observacoes}\n\nCancelamento: {motivo}".strip()
        ordem.save()

        return ordem

    @staticmethod
    @transaction.atomic
    def concluir(ordem: OrdemCompra) -> OrdemCompra:
        """
        Marca a ordem como concluída (entregue/finalizada).

        Args:
            ordem: OrdemCompra a ser concluída

        Returns:
            OrdemCompra: Ordem atualizada

        Raises:
            OrdemCompraServiceError: Se a ordem não puder ser concluída
        """
        if not ordem.pode_concluir:
            raise OrdemCompraServiceError(
                f"Ordem {ordem.numero} não pode ser concluída. Status atual: {ordem.status}",
            )

        ordem.status = StatusOrdemCompra.CONCLUIDA
        ordem.save()

        return ordem
