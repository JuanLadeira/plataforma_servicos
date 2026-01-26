
import pytest
from unittest.mock import patch

from plataforma_de_servicos.vendas.services.ordem_compra_service import OrdemCompraService, OrdemCompraServiceError
from plataforma_de_servicos.vendas.models import OrdemCompra, ItemOrdemCompra, StatusOrdemCompra
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.corretor.models import InteresseCompra, StatusInteresse, ItemInteresse

pytestmark = pytest.mark.django_db

@pytest.fixture
def usuario():
    """Cria um usuário simples para testes."""
    return User.objects.create_user(email='approver@example.com', password='password')

@pytest.fixture
def produto_teste():
    """Cria um produto de teste."""
    return Produto.objects.create(produto='Produto de Teste Final', preco=150.00, ncm='00001111')

@pytest.fixture
def ordem_compra_pendente(produto_teste):
    """
    Cria um Interesse de Compra e deixa o signal criar a Ordem de Compra associada.
    Retorna a Ordem de Compra com status PENDENTE_APROVACAO.
    """
    interesse = InteresseCompra.objects.create(
        nome_cliente='Cliente Pendente',
        email_cliente='pendente@example.com',
        telefone_cliente='11999991111',
        status=StatusInteresse.NOVO, # Começa como NOVO
        valor_total=produto_teste.preco
    )
    ItemInteresse.objects.create(
        interesse=interesse,
        produto_nome=produto_teste.produto,
        quantidade=1,
        preco_unitario=produto_teste.preco
    )
    # Altera o status para CONVERTIDO, o que dispara o signal
    interesse.status = StatusInteresse.CONVERTIDO
    interesse.save()
    
    # O signal post_save cria a ordem, então a buscamos a partir do interesse
    ordem = interesse.ordem_compra
    # Adiciona o produto real ao item da ordem, pois o signal não faz isso
    item_ordem = ordem.itens.first()
    item_ordem.produto = produto_teste
    item_ordem.save()

    return ordem

@pytest.fixture
def ordem_compra_aprovada(produto_teste, usuario):
    """
    Cria uma Ordem de Compra e a coloca no status APROVADA.
    """
    interesse = InteresseCompra.objects.create(
        nome_cliente='Cliente Aprovado',
        email_cliente='aprovado@example.com',
        telefone_cliente='11999992222',
        status=StatusInteresse.NOVO,
        valor_total=produto_teste.preco
    )
    ItemInteresse.objects.create(
        interesse=interesse,
        produto_nome=produto_teste.produto,
        quantidade=1,
        preco_unitario=produto_teste.preco
    )
    interesse.status = StatusInteresse.CONVERTIDO
    interesse.save()
    
    ordem = interesse.ordem_compra
    item_ordem = ordem.itens.first()
    item_ordem.produto = produto_teste
    item_ordem.save()

    # Aprova a ordem manualmente para o estado do teste
    ordem.status = StatusOrdemCompra.APROVADA
    ordem.aprovado_por = usuario
    ordem.save()
    
    return ordem


class TestOrdemCompraServiceAprovar:

    @patch('plataforma_de_servicos.vendas.services.ordem_compra_service.EstoqueService.criar_saida_por_pedido')
    def test_aprovar_ordem_pendente_deve_gerar_saida_estoque(self, mock_criar_saida, usuario, ordem_compra_pendente, produto_teste):
        """
        Verifica se ao aprovar uma ordem PENDENTE, a saída de estoque é gerada
        e o status da ordem é atualizado corretamente.
        """
        ordem = ordem_compra_pendente
        
        ordem_aprovada = OrdemCompraService.aprovar(ordem, usuario)

        mock_criar_saida.assert_called_once()
        
        itens_esperados = [{
            "produto": produto_teste,
            "variacao": None,
            "quantidade": 1,
        }]
        mock_criar_saida.assert_called_with(
            pedido_id=ordem.pk,
            itens_pedido=itens_esperados,
            funcionario=usuario
        )

        assert ordem_aprovada.status == StatusOrdemCompra.APROVADA
        assert ordem_aprovada.aprovado_por == usuario
        assert ordem_aprovada.data_aprovacao is not None

    @patch('plataforma_de_servicos.vendas.services.ordem_compra_service.EstoqueService.criar_saida_por_pedido')
    def test_aprovar_ordem_status_invalido_nao_deve_gerar_saida_estoque(self, mock_criar_saida, usuario, ordem_compra_aprovada):
        """
        Verifica se ao tentar aprovar uma ordem com status inválido (ex: APROVADA),
        um erro é lançado e a saída de estoque NÃO é gerada.
        Este teste irá falhar com a implementação atual, expondo o bug.
        """
        ordem = ordem_compra_aprovada

        with pytest.raises(OrdemCompraServiceError, match="não pode ser aprovada"):
            OrdemCompraService.aprovar(ordem, usuario)
        
        mock_criar_saida.assert_not_called()
