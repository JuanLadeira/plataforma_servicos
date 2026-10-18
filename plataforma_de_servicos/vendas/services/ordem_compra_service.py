"""
OrdemCompraService - Serviço para gerenciamento de Ordens de Compra.

Segue o padrão Model -> Service -> View, encapsulando toda a lógica de negócio
relacionada a ordens de compra, validação de estoque e fluxo de aprovação.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import F
from django.db.models import Sum
from django.utils import timezone

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.estoque.exceptions import InventarioSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import VariacaoSaldoInsuficienteError
from plataforma_de_servicos.estoque.services import EstoqueService
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra

if TYPE_CHECKING:
    from plataforma_de_servicos.empresa.models import Empresa


class OrdemCompraServiceError(Exception):
    """Exceção base para erros do serviço de OrdemCompra."""


class EstoqueInsuficienteError(OrdemCompraServiceError):
    """Erro quando não há estoque suficiente para aprovar a ordem."""


ERROS_DE_SALDO = (
    InventarioSaldoInsuficienteError,
    ProdutoSaldoInsuficienteError,
    VariacaoSaldoInsuficienteError,
)


@dataclass
class StockValidationItem:
    """Resultado da validação de estoque de um item."""
    produto_nome: str
    variacao_info: str
    quantidade_solicitada: int
    quantidade_disponivel: int
    is_valid: bool

    @property
    def deficit(self) -> int:
        """Retorna o déficit de estoque (quantidade faltante)."""
        return max(0, self.quantidade_solicitada - self.quantidade_disponivel)


@dataclass
class StockValidationResult:
    """Resultado da validação de estoque de uma ordem."""
    is_valid: bool
    items: list[StockValidationItem]
    message: str

    @property
    def invalid_items(self) -> list[StockValidationItem]:
        """Retorna apenas os itens com estoque insuficiente."""
        return [item for item in self.items if not item.is_valid]


def _buscar_produto_e_variacao(
    produto_nome: str, variacao_info: str, empresa,
) -> tuple[Produto | None, VariacaoProduto | None]:
    """
    Busca o produto pelo nome e a variação pelas informações de atributos.

    Args:
        produto_nome: Nome do produto
        variacao_info: String com informações da variação (ex: "Cor: Azul, Tamanho: M")
        empresa: Empresa dona do produto (nunca busca em outras empresas)

    Returns:
        Tupla com (Produto, VariacaoProduto) ou (None, None) se não encontrar
    """
    if empresa is None:
        return None, None

    # Buscar produto pelo nome exato, dentro da empresa
    produto = Produto.objects.filter(empresa=empresa, produto=produto_nome).first()
    if produto is None:
        return None, None

    # Se não há informação de variação, retornar só o produto
    if not variacao_info or not variacao_info.strip():
        return produto, None

    # Buscar variação que corresponda aos atributos
    # variacao_info tem formato "Cor: Azul, Tamanho: M"
    # ValorAtributo.__str__ retorna "Atributo: Valor"
    valores_busca = [v.strip() for v in variacao_info.split(",")]

    for variacao in produto.variacoes.prefetch_related("valores", "valores__atributo").all():
        valores_variacao = [str(v) for v in variacao.valores.all()]
        # Verificar se todos os valores buscados estão na variação
        if set(valores_busca) == set(valores_variacao):
            return produto, variacao

    # Se não encontrou variação correspondente, retornar só o produto
    return produto, None


class OrdemCompraService:
    """
    Serviço para gerenciar operações de OrdemCompra.

    Responsabilidades:
    - Geração de números de ordem
    - Criação de ordens a partir de interesses
    - Validação de estoque antes da aprovação
    - Fluxo de status (aprovar, rejeitar, faturar, cancelar, concluir)

    As transições recarregam a ordem com select_for_update() e checam o status
    no registro travado, para que duas operações simultâneas não passem as duas.
    """

    @staticmethod
    def _travar(ordem: OrdemCompra) -> OrdemCompra:
        return OrdemCompra.objects.select_for_update().get(pk=ordem.pk)

    @staticmethod
    def _deposito_padrao(empresa) -> Inventario:
        try:
            return Inventario.objects.padrao_da_empresa(empresa)
        except InventarioPadraoAusenteError as exc:
            raise OrdemCompraServiceError(str(exc)) from exc

    @staticmethod
    def validar_estoque(ordem: OrdemCompra) -> StockValidationResult:
        """
        Valida se há estoque suficiente para todos os itens da ordem.

        Consulta o saldo do depósito padrão da empresa da ordem, que é o mesmo
        número que a aprovação vai checar com as linhas travadas.

        Args:
            ordem: OrdemCompra a ser validada

        Returns:
            StockValidationResult com detalhes da validação
        """
        try:
            deposito = OrdemCompraService._deposito_padrao(ordem.empresa)
        except OrdemCompraServiceError as exc:
            return StockValidationResult(is_valid=False, items=[], message=str(exc))

        items_validation: list[StockValidationItem] = []
        all_valid = True

        for item in ordem.itens.select_related("produto", "variacao").all():
            if not item.produto:
                # Item sem produto vinculado, não validar
                continue

            estoque_disponivel = OrdemCompraService.obter_estoque_disponivel_item(
                item.produto, item.variacao, deposito.pk,
            )

            is_valid = item.quantidade <= estoque_disponivel

            items_validation.append(StockValidationItem(
                produto_nome=item.produto_nome,
                variacao_info=item.variacao_info or "",
                quantidade_solicitada=item.quantidade,
                quantidade_disponivel=estoque_disponivel,
                is_valid=is_valid,
            ))

            if not is_valid:
                all_valid = False

        if all_valid:
            message = "Estoque validado com sucesso. Todos os itens estão disponíveis."
        else:
            invalid_count = len([i for i in items_validation if not i.is_valid])
            message = f"Estoque insuficiente para {invalid_count} item(s)."

        return StockValidationResult(
            is_valid=all_valid,
            items=items_validation,
            message=message,
        )

    @staticmethod
    def obter_estoque_disponivel_item(
        produto: Produto,
        variacao: VariacaoProduto | None = None,
        inventario_id: int | None = None,
    ) -> int:
        """
        Obtém o estoque disponível para um item específico.

        Args:
            produto: Produto para verificar
            variacao: Variação específica (opcional)
            inventario_id: ID do inventário específico (opcional)

        Returns:
            Quantidade disponível em estoque
        """
        if inventario_id:
            # Buscar em inventário específico
            saldo = InventarioSaldo.objects.filter(
                inventario_id=inventario_id,
                produto=produto,
            )
            if variacao:
                saldo = saldo.filter(variacao=variacao)
            else:
                saldo = saldo.filter(variacao__isnull=True)

            result = saldo.aggregate(total=Sum("quantidade"))
            return result["total"] or 0

        # Buscar estoque total (campo no modelo)
        if variacao:
            return variacao.estoque
        return produto.estoque

    @staticmethod
    def gerar_numero(empresa) -> str:
        """
        Gera número único por empresa no formato OC-YYYY-NNNNN.

        Args:
            empresa: Empresa para qual gerar o número

        Returns:
            str: Número da ordem (ex: OC-2026-00001)
        """
        ano = timezone.now().year
        prefixo = f"OC-{ano}-"

        ultima_ordem = (
            OrdemCompra.objects.filter(
                empresa=empresa,
                numero__startswith=prefixo,
            )
            .order_by("-numero")
            .first()
        )

        if ultima_ordem:
            try:
                ultimo_numero = int(ultima_ordem.numero.split("-")[-1])
                novo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                novo_numero = 1
        else:
            novo_numero = 1

        return f"{prefixo}{novo_numero:05d}"

    @staticmethod
    @transaction.atomic
    def criar_ordem_manual(
        empresa: "Empresa",
        nome_cliente: str,
        itens: list[dict],
        email_cliente: str = "",
        telefone_cliente: str = "",
        corretor=None,
        inventario_origem_id: int | None = None,
        validate_stock: bool = True,
    ) -> OrdemCompra:
        """
        Cria uma ordem de compra avulsa (manual).

        Args:
            empresa: Empresa dona da ordem
            nome_cliente: Nome do cliente
            itens: Lista de dicts com {produto_id, variacao_id, quantidade, preco_unitario}
            email_cliente: Email do cliente (opcional)
            telefone_cliente: Telefone do cliente (opcional)
            corretor: Funcionário responsável (opcional)
            inventario_origem_id: ID do inventário usado na validação (padrão: depósito padrão da empresa)
            validate_stock: Se True, valida estoque antes de criar

        Returns:
            OrdemCompra: Ordem criada

        Raises:
            OrdemCompraServiceError: Se dados inválidos
            EstoqueInsuficienteError: Se estoque insuficiente
        """
        if not itens:
            raise OrdemCompraServiceError("É necessário informar ao menos um item.")

        if not nome_cliente:
            raise OrdemCompraServiceError("Nome do cliente é obrigatório.")

        if validate_stock and inventario_origem_id is None:
            inventario_origem_id = OrdemCompraService._deposito_padrao(empresa).pk

        # Validar itens e calcular valor total
        valor_total = Decimal("0.00")
        itens_validados = []

        for item_data in itens:
            produto_id = item_data.get("produto_id")
            variacao_id = item_data.get("variacao_id")
            quantidade = item_data.get("quantidade", 1)
            preco_unitario = Decimal(str(item_data.get("preco_unitario", 0)))

            if not produto_id:
                raise OrdemCompraServiceError("ID do produto é obrigatório em cada item.")

            try:
                produto = Produto.objects.get(id=produto_id, empresa=empresa)
            except Produto.DoesNotExist:
                raise OrdemCompraServiceError(f"Produto #{produto_id} não encontrado.")

            variacao = None
            if variacao_id:
                try:
                    variacao = VariacaoProduto.objects.get(id=variacao_id, produto=produto)
                except VariacaoProduto.DoesNotExist:
                    raise OrdemCompraServiceError(
                        f"Variação #{variacao_id} não encontrada para o produto."
                    )

            # Validar estoque se solicitado
            if validate_stock:
                estoque_disponivel = OrdemCompraService.obter_estoque_disponivel_item(
                    produto, variacao, inventario_origem_id
                )
                if quantidade > estoque_disponivel:
                    nome_item = produto.produto
                    if variacao:
                        nome_item += f" ({variacao})"
                    raise EstoqueInsuficienteError(
                        f"Estoque insuficiente para '{nome_item}'. "
                        f"Solicitado: {quantidade}, Disponível: {estoque_disponivel}"
                    )

            # Calcular preço se não informado
            if not preco_unitario:
                if variacao:
                    preco_unitario = variacao.calcular_preco_final()
                else:
                    preco_unitario = produto.preco or Decimal("0.00")

            itens_validados.append({
                "produto": produto,
                "variacao": variacao,
                "quantidade": quantidade,
                "preco_unitario": preco_unitario,
            })

            valor_total += preco_unitario * quantidade

        # Criar ordem
        ordem = OrdemCompra.objects.create(
            numero=OrdemCompraService.gerar_numero(empresa),
            empresa=empresa,
            nome_cliente=nome_cliente,
            email_cliente=email_cliente,
            telefone_cliente=telefone_cliente,
            valor_total=valor_total,
            status=StatusOrdemCompra.PENDENTE_APROVACAO,
            corretor=corretor,
        )

        # Criar itens
        for item_data in itens_validados:
            produto = item_data["produto"]
            variacao = item_data["variacao"]

            variacao_info = ""
            if variacao:
                variacao_info = ", ".join(str(v) for v in variacao.valores.all())

            ItemOrdemCompra.objects.create(
                ordem=ordem,
                produto=produto,
                variacao=variacao,
                produto_nome=produto.produto,
                variacao_info=variacao_info,
                quantidade=item_data["quantidade"],
                preco_unitario=item_data["preco_unitario"],
            )

        return ordem

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
            numero=OrdemCompraService.gerar_numero(interesse.empresa),
            empresa=interesse.empresa,
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
            # Tentar vincular ao produto e variação reais
            produto, variacao = _buscar_produto_e_variacao(
                item_interesse.produto_nome,
                item_interesse.variacao_info,
                interesse.empresa,
            )

            ItemOrdemCompra.objects.create(
                ordem=ordem,
                produto=produto,
                variacao=variacao,
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
        Aprova a ordem numa única transação: saída de estoque, status e comissão.

        A ordem é recarregada travada, então uma segunda aprovação simultânea
        espera e depois falha. A baixa sai do depósito padrão da empresa da ordem
        e o saldo é checado sobre as linhas travadas (ver Estoque.processar).
        Qualquer erro desfaz tudo.

        Args:
            ordem: OrdemCompra a ser aprovada
            usuario: Usuário que está aprovando

        Returns:
            OrdemCompra: Ordem atualizada

        Raises:
            OrdemCompraServiceError: Se a ordem não puder ser aprovada ou a empresa
                                     não tiver depósito padrão
            EstoqueInsuficienteError: Se não houver estoque suficiente no depósito padrão
        """
        travada = OrdemCompraService._travar(ordem)
        if not travada.pode_aprovar:
            raise OrdemCompraServiceError(
                f"Ordem {travada.numero} não pode ser aprovada. "
                f"Status atual: {travada.get_status_display()}",
            )

        deposito = OrdemCompraService._deposito_padrao(travada.empresa)

        itens_pedido = [
            {"produto": item.produto, "variacao": item.variacao, "quantidade": item.quantidade}
            for item in travada.itens.select_related("produto", "variacao").all()
            if item.produto
        ]
        if itens_pedido:
            try:
                EstoqueService.criar_saida_por_ordem_compra(
                    ordem_compra=travada,
                    itens_pedido=itens_pedido,
                    funcionario=usuario,
                    inventario_origem=deposito,
                )
            except ERROS_DE_SALDO as exc:
                raise EstoqueInsuficienteError(
                    f"Não é possível aprovar a ordem {travada.numero}. {exc}",
                ) from exc

        travada.status = StatusOrdemCompra.APROVADA
        travada.aprovado_por = usuario
        travada.data_aprovacao = timezone.now()
        travada.save(update_fields=["status", "aprovado_por", "data_aprovacao", "modified"])

        if travada.corretor:
            from plataforma_de_servicos.vendas.services.commission_service import CommissionService
            CommissionService(travada.empresa).criar_comissao(travada)

        ordem.refresh_from_db()
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
