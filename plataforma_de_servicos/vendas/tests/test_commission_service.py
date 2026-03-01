"""
Testes para o CommissionService.

Cobre todos os métodos do serviço de comissões:
- obter_percentual (hierarquia: vendedor > categoria > padrão)
- calcular_comissao
- criar_comissao
- recalcular_comissao
- aprovar_comissao
- pagar_comissao
- cancelar_comissao
- listar_comissoes_pendentes
- resumo_comissoes
"""
from decimal import Decimal

import pytest

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.users.models import Funcionario
from plataforma_de_servicos.users.models import PapelFuncionario
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.comissao import Comissao
from plataforma_de_servicos.vendas.models.comissao import ComissaoCategoria
from plataforma_de_servicos.vendas.models.comissao import ComissaoVendedor
from plataforma_de_servicos.vendas.models.comissao import ConfiguracaoComissao
from plataforma_de_servicos.vendas.models.comissao import StatusComissao
from plataforma_de_servicos.vendas.services.commission_service import CommissionService

pytestmark = pytest.mark.django_db


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def empresa():
    """Cria uma empresa para testes."""
    return Empresa.objects.create(nome="Empresa Teste", slug="empresa-teste")


@pytest.fixture
def usuario(empresa):
    """Cria um usuário para testes."""
    return User.objects.create_user(
        email="vendedor@teste.com",
        password="senha123",
    )


@pytest.fixture
def funcionario(usuario, empresa):
    """Cria um funcionário/vendedor para testes."""
    usuario.name = "Vendedor Teste"
    usuario.save()
    return Funcionario.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=PapelFuncionario.VENDEDOR,
    )


@pytest.fixture
def categoria(empresa):
    """Cria uma categoria para testes."""
    return Categoria.objects.create(
        categoria="Categoria Teste",
        empresa=empresa,
    )


@pytest.fixture
def produto(empresa, categoria):
    """Cria um produto para testes."""
    return Produto.objects.create(
        produto="Produto Teste",
        preco=Decimal("100.00"),
        empresa=empresa,
        categoria=categoria,
        ncm="12345678",
        estoque=10,
    )


@pytest.fixture
def interesse_compra(empresa, funcionario, produto):
    """Cria um interesse de compra para testes."""
    interesse = InteresseCompra.objects.create(
        empresa=empresa,
        nome_cliente="Cliente Teste",
        email_cliente="cliente@teste.com",
        telefone_cliente="11999999999",
        valor_total=Decimal("500.00"),
        status=StatusInteresse.NOVO,
        corretor=funcionario,
    )
    ItemInteresse.objects.create(
        interesse=interesse,
        produto_nome=produto.produto,
        quantidade=5,
        preco_unitario=Decimal("100.00"),
    )
    return interesse


@pytest.fixture
def ordem_compra(empresa, funcionario, produto, interesse_compra):
    """Cria uma ordem de compra para testes."""
    ordem = OrdemCompra.objects.create(
        numero="OC-2026-00001",
        empresa=empresa,
        interesse=interesse_compra,
        nome_cliente="Cliente Teste",
        email_cliente="cliente@teste.com",
        telefone_cliente="11999999999",
        valor_total=Decimal("500.00"),
        status=StatusOrdemCompra.APROVADA,
        corretor=funcionario,
    )
    # Adiciona um item à ordem
    ItemOrdemCompra.objects.create(
        ordem=ordem,
        produto=produto,
        produto_nome=produto.produto,
        quantidade=5,
        preco_unitario=Decimal("100.00"),
    )
    return ordem


@pytest.fixture
def configuracao_comissao(empresa):
    """Cria configuração de comissão para testes."""
    return ConfiguracaoComissao.objects.create(
        empresa=empresa,
        percentual_padrao=Decimal("5.00"),
    )


@pytest.fixture
def service(empresa):
    """Cria uma instância do CommissionService."""
    return CommissionService(empresa)


# ============================================
# Testes: obter_percentual
# ============================================


class TestObterPercentual:
    """Testes para o método obter_percentual."""

    def test_sem_configuracao_retorna_zero(self, service, funcionario):
        """Sem configuração de comissão, deve retornar 0."""
        percentual, fonte = service.obter_percentual(funcionario)

        assert percentual == Decimal("0.00")
        assert fonte == "sem_configuracao"

    def test_retorna_percentual_padrao(self, service, funcionario, configuracao_comissao):
        """Deve retornar o percentual padrão da empresa."""
        percentual, fonte = service.obter_percentual(funcionario)

        assert percentual == Decimal("5.00")
        assert fonte == "padrao"

    def test_percentual_categoria_tem_prioridade_sobre_padrao(
        self, service, funcionario, configuracao_comissao, categoria
    ):
        """Percentual por categoria deve ter prioridade sobre o padrão."""
        ComissaoCategoria.objects.create(
            configuracao=configuracao_comissao,
            categoria=categoria,
            percentual=Decimal("8.00"),
        )

        percentual, fonte = service.obter_percentual(funcionario, categoria.id)

        assert percentual == Decimal("8.00")
        assert fonte == "categoria"

    def test_percentual_vendedor_tem_prioridade_sobre_categoria(
        self, service, funcionario, configuracao_comissao, categoria
    ):
        """Percentual específico do vendedor deve ter prioridade sobre categoria."""
        ComissaoCategoria.objects.create(
            configuracao=configuracao_comissao,
            categoria=categoria,
            percentual=Decimal("8.00"),
        )
        ComissaoVendedor.objects.create(
            configuracao=configuracao_comissao,
            funcionario=funcionario,
            percentual=Decimal("10.00"),
        )

        percentual, fonte = service.obter_percentual(funcionario, categoria.id)

        assert percentual == Decimal("10.00")
        assert fonte == "vendedor"

    def test_sem_categoria_retorna_padrao(self, service, funcionario, configuracao_comissao):
        """Sem categoria informada, deve usar o percentual padrão."""
        percentual, fonte = service.obter_percentual(funcionario, categoria_id=None)

        assert percentual == Decimal("5.00")
        assert fonte == "padrao"


# ============================================
# Testes: calcular_comissao
# ============================================


class TestCalcularComissao:
    """Testes para o método calcular_comissao."""

    def test_calculo_com_percentual_padrao(
        self, service, funcionario, ordem_compra, configuracao_comissao
    ):
        """Deve calcular a comissão com o percentual padrão."""
        calculo = service.calcular_comissao(ordem_compra, funcionario)

        assert calculo.percentual == Decimal("5.00")
        assert calculo.valor_base == Decimal("500.00")
        assert calculo.valor_comissao == Decimal("25.00")  # 500 * 5% = 25
        assert calculo.fonte_percentual == "padrao"

    def test_calculo_com_percentual_categoria(
        self, service, funcionario, ordem_compra, configuracao_comissao, categoria
    ):
        """Deve calcular a comissão com o percentual da categoria."""
        ComissaoCategoria.objects.create(
            configuracao=configuracao_comissao,
            categoria=categoria,
            percentual=Decimal("10.00"),
        )

        calculo = service.calcular_comissao(ordem_compra, funcionario)

        assert calculo.percentual == Decimal("10.00")
        assert calculo.valor_comissao == Decimal("50.00")  # 500 * 10% = 50
        assert calculo.fonte_percentual == "categoria"

    def test_calculo_sem_configuracao(self, service, funcionario, ordem_compra):
        """Sem configuração, deve retornar comissão zero."""
        calculo = service.calcular_comissao(ordem_compra, funcionario)

        assert calculo.percentual == Decimal("0.00")
        assert calculo.valor_comissao == Decimal("0.00")
        assert calculo.fonte_percentual == "sem_configuracao"


# ============================================
# Testes: criar_comissao
# ============================================


class TestCriarComissao:
    """Testes para o método criar_comissao."""

    def test_criar_comissao_sucesso(
        self, service, funcionario, ordem_compra, configuracao_comissao
    ):
        """Deve criar comissão com sucesso."""
        result = service.criar_comissao(ordem_compra, funcionario)

        assert result.success is True
        assert result.comissao is not None
        assert result.comissao.percentual == Decimal("5.00")
        assert result.comissao.valor_comissao == Decimal("25.00")
        assert result.comissao.status == StatusComissao.PENDENTE

    def test_criar_comissao_usa_corretor_da_ordem(
        self, service, ordem_compra, configuracao_comissao
    ):
        """Deve usar o corretor da ordem se funcionário não for informado."""
        result = service.criar_comissao(ordem_compra)

        assert result.success is True
        assert result.comissao.funcionario == ordem_compra.corretor

    def test_criar_comissao_sem_corretor_falha(
        self, service, empresa, configuracao_comissao
    ):
        """Sem corretor, deve falhar."""
        # Cria interesse sem corretor
        interesse = InteresseCompra.objects.create(
            empresa=empresa,
            nome_cliente="Cliente Sem Corretor",
            email_cliente="sem@corretor.com",
            telefone_cliente="11888888888",
            valor_total=Decimal("100.00"),
            status=StatusInteresse.NOVO,
        )
        ordem_sem_corretor = OrdemCompra.objects.create(
            numero="OC-2026-00002",
            empresa=empresa,
            interesse=interesse,
            nome_cliente="Cliente Sem Corretor",
            email_cliente="sem@corretor.com",
            telefone_cliente="11888888888",
            valor_total=Decimal("100.00"),
            status=StatusOrdemCompra.APROVADA,
        )

        result = service.criar_comissao(ordem_sem_corretor)

        assert result.success is False
        assert "vendedor/corretor" in result.message

    def test_criar_comissao_duplicada_falha(
        self, service, funcionario, ordem_compra, configuracao_comissao
    ):
        """Não deve permitir criar comissão duplicada."""
        # Primeira criação
        service.criar_comissao(ordem_compra, funcionario)

        # Segunda tentativa
        result = service.criar_comissao(ordem_compra, funcionario)

        assert result.success is False
        assert "Já existe comissão" in result.message

    def test_criar_comissao_percentual_zero_falha(
        self, service, funcionario, ordem_compra
    ):
        """Sem configuração (percentual zero), deve falhar."""
        result = service.criar_comissao(ordem_compra, funcionario)

        assert result.success is False
        assert "zero" in result.message


# ============================================
# Testes: recalcular_comissao
# ============================================


class TestRecalcularComissao:
    """Testes para o método recalcular_comissao."""

    @pytest.fixture
    def comissao_pendente(self, service, funcionario, ordem_compra, configuracao_comissao):
        """Cria uma comissão pendente para testes."""
        result = service.criar_comissao(ordem_compra, funcionario)
        return result.comissao

    def test_recalcular_com_novo_percentual(self, service, comissao_pendente):
        """Deve recalcular com novo percentual."""
        result = service.recalcular_comissao(
            comissao_pendente,
            novo_percentual=Decimal("10.00"),
        )

        assert result.success is True
        assert result.comissao.percentual == Decimal("10.00")
        assert result.comissao.valor_comissao == Decimal("50.00")  # 500 * 10% = 50

    def test_recalcular_sem_alterar_percentual(self, service, comissao_pendente):
        """Sem novo percentual, deve recalcular com o atual."""
        # Altera o valor_base manualmente para simular recálculo
        comissao_pendente.valor_base = Decimal("1000.00")
        comissao_pendente.save()

        result = service.recalcular_comissao(comissao_pendente)

        assert result.success is True
        # 1000 * 5% = 50
        assert result.comissao.valor_comissao == Decimal("50.00")

    def test_recalcular_comissao_nao_pendente_falha(
        self, service, comissao_pendente
    ):
        """Não deve recalcular comissão que não está pendente."""
        comissao_pendente.status = StatusComissao.APROVADA
        comissao_pendente.save()

        result = service.recalcular_comissao(comissao_pendente)

        assert result.success is False
        assert "pendentes" in result.message


# ============================================
# Testes: aprovar_comissao
# ============================================


class TestAprovarComissao:
    """Testes para o método aprovar_comissao."""

    @pytest.fixture
    def comissao_pendente(self, service, funcionario, ordem_compra, configuracao_comissao):
        """Cria uma comissão pendente para testes."""
        result = service.criar_comissao(ordem_compra, funcionario)
        return result.comissao

    def test_aprovar_comissao_sucesso(self, service, comissao_pendente):
        """Deve aprovar comissão pendente."""
        result = service.aprovar_comissao(comissao_pendente)

        assert result.success is True
        assert result.comissao.status == StatusComissao.APROVADA
        assert result.comissao.data_aprovacao is not None

    def test_aprovar_comissao_ja_aprovada_falha(self, service, comissao_pendente):
        """Não deve aprovar comissão já aprovada."""
        service.aprovar_comissao(comissao_pendente)

        result = service.aprovar_comissao(comissao_pendente)

        assert result.success is False
        assert "não pode ser aprovada" in result.message


# ============================================
# Testes: pagar_comissao
# ============================================


class TestPagarComissao:
    """Testes para o método pagar_comissao."""

    @pytest.fixture
    def comissao_aprovada(self, service, funcionario, ordem_compra, configuracao_comissao):
        """Cria uma comissão aprovada para testes."""
        result = service.criar_comissao(ordem_compra, funcionario)
        service.aprovar_comissao(result.comissao)
        return result.comissao

    def test_pagar_comissao_sucesso(self, service, comissao_aprovada):
        """Deve pagar comissão aprovada."""
        result = service.pagar_comissao(comissao_aprovada)

        assert result.success is True
        assert result.comissao.status == StatusComissao.PAGA
        assert result.comissao.data_pagamento is not None

    def test_pagar_comissao_pendente_falha(self, service, funcionario, ordem_compra, configuracao_comissao):
        """Não deve pagar comissão pendente (não aprovada)."""
        result = service.criar_comissao(ordem_compra, funcionario)
        comissao = result.comissao

        result = service.pagar_comissao(comissao)

        assert result.success is False
        assert "não pode ser paga" in result.message


# ============================================
# Testes: cancelar_comissao
# ============================================


class TestCancelarComissao:
    """Testes para o método cancelar_comissao."""

    @pytest.fixture
    def comissao_pendente(self, service, funcionario, ordem_compra, configuracao_comissao):
        """Cria uma comissão pendente para testes."""
        result = service.criar_comissao(ordem_compra, funcionario)
        return result.comissao

    def test_cancelar_comissao_pendente(self, service, comissao_pendente):
        """Deve cancelar comissão pendente."""
        result = service.cancelar_comissao(comissao_pendente)

        assert result.success is True
        assert result.comissao.status == StatusComissao.CANCELADA

    def test_cancelar_comissao_com_motivo(self, service, comissao_pendente):
        """Deve registrar o motivo do cancelamento."""
        result = service.cancelar_comissao(
            comissao_pendente,
            motivo="Cliente cancelou o pedido",
        )

        assert result.success is True
        assert "Cliente cancelou o pedido" in result.comissao.observacoes

    def test_cancelar_comissao_aprovada(self, service, comissao_pendente):
        """Deve cancelar comissão aprovada."""
        service.aprovar_comissao(comissao_pendente)

        result = service.cancelar_comissao(comissao_pendente)

        assert result.success is True
        assert result.comissao.status == StatusComissao.CANCELADA

    def test_cancelar_comissao_paga_falha(self, service, comissao_pendente):
        """Não deve cancelar comissão já paga."""
        service.aprovar_comissao(comissao_pendente)
        service.pagar_comissao(comissao_pendente)

        result = service.cancelar_comissao(comissao_pendente)

        assert result.success is False
        assert "não pode ser cancelada" in result.message


# ============================================
# Testes: listar_comissoes_pendentes
# ============================================


class TestListarComissoesPendentes:
    """Testes para o método listar_comissoes_pendentes."""

    def test_lista_apenas_pendentes(
        self, service, funcionario, ordem_compra, configuracao_comissao, empresa
    ):
        """Deve listar apenas comissões pendentes."""
        # Cria comissão pendente
        result = service.criar_comissao(ordem_compra, funcionario)
        comissao_pendente = result.comissao

        # Cria outra ordem e aprova a comissão
        interesse2 = InteresseCompra.objects.create(
            empresa=empresa,
            nome_cliente="Cliente 2",
            email_cliente="cliente2@teste.com",
            telefone_cliente="11777777777",
            valor_total=Decimal("200.00"),
            status=StatusInteresse.NOVO,
            corretor=funcionario,
        )
        ordem2 = OrdemCompra.objects.create(
            numero="OC-2026-00002",
            empresa=empresa,
            interesse=interesse2,
            nome_cliente="Cliente 2",
            email_cliente="cliente2@teste.com",
            telefone_cliente="11777777777",
            valor_total=Decimal("200.00"),
            status=StatusOrdemCompra.APROVADA,
            corretor=funcionario,
        )
        result2 = service.criar_comissao(ordem2, funcionario)
        service.aprovar_comissao(result2.comissao)

        pendentes = service.listar_comissoes_pendentes()

        assert len(pendentes) == 1
        assert pendentes[0] == comissao_pendente

    def test_lista_vazia_sem_pendentes(self, service, configuracao_comissao):
        """Deve retornar lista vazia se não houver pendentes."""
        pendentes = service.listar_comissoes_pendentes()

        assert len(pendentes) == 0


# ============================================
# Testes: resumo_comissoes
# ============================================


class TestResumoComissoes:
    """Testes para o método resumo_comissoes."""

    def test_resumo_basico(
        self, service, funcionario, ordem_compra, configuracao_comissao
    ):
        """Deve retornar resumo de comissões."""
        service.criar_comissao(ordem_compra, funcionario)

        resumo = service.resumo_comissoes()

        assert resumo["quantidade_total"] == 1
        assert resumo["total_geral"] == Decimal("25.00")
        assert StatusComissao.PENDENTE in resumo["por_status"]

    def test_resumo_por_status(
        self, service, funcionario, ordem_compra, configuracao_comissao, empresa
    ):
        """Deve agrupar por status."""
        # Comissão pendente
        result1 = service.criar_comissao(ordem_compra, funcionario)

        # Comissão aprovada
        interesse2 = InteresseCompra.objects.create(
            empresa=empresa,
            nome_cliente="Cliente 2",
            email_cliente="cliente2@teste.com",
            telefone_cliente="11666666666",
            valor_total=Decimal("200.00"),
            status=StatusInteresse.NOVO,
            corretor=funcionario,
        )
        ordem2 = OrdemCompra.objects.create(
            numero="OC-2026-00002",
            empresa=empresa,
            interesse=interesse2,
            nome_cliente="Cliente 2",
            email_cliente="cliente2@teste.com",
            telefone_cliente="11666666666",
            valor_total=Decimal("200.00"),
            status=StatusOrdemCompra.APROVADA,
            corretor=funcionario,
        )
        result2 = service.criar_comissao(ordem2, funcionario)
        service.aprovar_comissao(result2.comissao)

        resumo = service.resumo_comissoes()

        assert resumo["quantidade_total"] == 2
        assert StatusComissao.PENDENTE in resumo["por_status"]
        assert StatusComissao.APROVADA in resumo["por_status"]

    def test_resumo_filtrado_por_funcionario(
        self, service, funcionario, ordem_compra, configuracao_comissao, empresa, usuario
    ):
        """Deve filtrar por funcionário."""
        # Comissão do funcionário 1
        service.criar_comissao(ordem_compra, funcionario)

        # Outro funcionário
        usuario2 = User.objects.create_user(email="outro@teste.com", password="123", name="Outro Vendedor")
        funcionario2 = Funcionario.objects.create(
            usuario=usuario2,
            empresa=empresa,
            papel=PapelFuncionario.VENDEDOR,
        )
        interesse2 = InteresseCompra.objects.create(
            empresa=empresa,
            nome_cliente="Cliente 2",
            email_cliente="cliente2@teste.com",
            telefone_cliente="11555555555",
            valor_total=Decimal("300.00"),
            status=StatusInteresse.NOVO,
            corretor=funcionario2,
        )
        ordem2 = OrdemCompra.objects.create(
            numero="OC-2026-00002",
            empresa=empresa,
            interesse=interesse2,
            nome_cliente="Cliente 2",
            email_cliente="cliente2@teste.com",
            telefone_cliente="11555555555",
            valor_total=Decimal("300.00"),
            status=StatusOrdemCompra.APROVADA,
            corretor=funcionario2,
        )
        service.criar_comissao(ordem2, funcionario2)

        resumo = service.resumo_comissoes(funcionario=funcionario)

        assert resumo["quantidade_total"] == 1
        assert resumo["total_geral"] == Decimal("25.00")

    def test_resumo_sem_comissoes(self, service):
        """Deve retornar resumo vazio."""
        resumo = service.resumo_comissoes()

        assert resumo["quantidade_total"] == 0
        assert resumo["total_geral"] == Decimal("0.00")
        assert resumo["por_status"] == {}
