from decimal import Decimal

import pytest
from django.utils import timezone

from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.corretor.tests.factories import ItemInteresseFactory
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.produto.tests.factories import AtributoFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import ValorAtributoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services import OrdemCompraService
from plataforma_de_servicos.vendas.services import OrdemCompraServiceError
from plataforma_de_servicos.vendas.tests.factories import OrdemCompraFactory


@pytest.mark.django_db
class TestOrdemCompraModel:
    def test_str_representation(self):
        ordem = OrdemCompraFactory(numero="OC-2026-00001", nome_cliente="João Silva")
        assert str(ordem) == "OC-2026-00001 - João Silva"

    def test_pode_aprovar_when_pendente(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        assert ordem.pode_aprovar is True

    def test_pode_aprovar_when_not_pendente(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        assert ordem.pode_aprovar is False

    def test_pode_faturar_when_aprovada(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        assert ordem.pode_faturar is True

    def test_pode_faturar_when_not_aprovada(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        assert ordem.pode_faturar is False


@pytest.mark.django_db
class TestOrdemCompraServiceGerarNumero:
    def test_gerar_numero_formato(self):
        empresa = EmpresaFactory()
        numero = OrdemCompraService.gerar_numero(empresa)
        ano = timezone.now().year
        assert numero.startswith(f"OC-{ano}-")
        assert len(numero) == 13  # OC-YYYY-NNNNN

    def test_gerar_numero_incrementa(self):
        empresa = EmpresaFactory()
        OrdemCompraFactory(numero="OC-2026-00001", empresa=empresa)
        numero = OrdemCompraService.gerar_numero(empresa)
        assert numero == "OC-2026-00002"

    def test_gerar_numero_primeiro_do_ano(self):
        empresa = EmpresaFactory()
        # Sem ordens existentes para esta empresa
        numero = OrdemCompraService.gerar_numero(empresa)
        ano = timezone.now().year
        assert numero == f"OC-{ano}-00001"

    def test_gerar_numero_isolado_por_empresa(self):
        """Cada empresa tem sua própria sequência de números."""
        empresa1 = EmpresaFactory()
        empresa2 = EmpresaFactory()

        # Criar ordens para empresa1
        OrdemCompraFactory(numero="OC-2026-00001", empresa=empresa1)
        OrdemCompraFactory(numero="OC-2026-00002", empresa=empresa1)

        # Empresa2 deve começar do 00001
        numero = OrdemCompraService.gerar_numero(empresa2)
        ano = timezone.now().year
        assert numero == f"OC-{ano}-00001"

        # Empresa1 deve continuar do 00003
        numero = OrdemCompraService.gerar_numero(empresa1)
        assert numero == "OC-2026-00003"


@pytest.mark.django_db
class TestOrdemCompraServiceCriarOrdem:
    def test_criar_ordem_de_interesse_sucesso(self):
        """Testa criação via signal quando interesse é convertido."""
        funcionario = FuncionarioFactory(is_corretor=True)
        empresa = EmpresaFactory()
        # Criar interesse como NOVO primeiro
        interesse = InteresseCompraFactory(
            status=StatusInteresse.NOVO,
            corretor=funcionario,
            empresa=empresa,
            valor_total=Decimal("150.00"),
        )
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Produto Teste",
            quantidade=2,
            preco_unitario=Decimal("75.00"),
        )

        # Converter dispara o signal que cria a ordem
        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        # Buscar a ordem criada pelo signal
        ordem = interesse.ordem_compra

        assert ordem.interesse == interesse
        assert ordem.nome_cliente == interesse.nome_cliente
        assert ordem.email_cliente == interesse.email_cliente
        assert ordem.telefone_cliente == interesse.telefone_cliente
        assert ordem.valor_total == interesse.valor_total
        assert ordem.corretor == funcionario
        assert ordem.status == StatusOrdemCompra.PENDENTE_APROVACAO
        assert ordem.itens.count() == 1

    def test_criar_ordem_copia_itens(self):
        """Testa que os itens são copiados corretamente."""
        # Criar interesse como NOVO primeiro
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Pizza Margherita",
            variacao_info="Tamanho: Grande",
            quantidade=2,
            preco_unitario=Decimal("45.00"),
        )
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Refrigerante",
            quantidade=3,
            preco_unitario=Decimal("8.00"),
        )

        # Converter dispara o signal
        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        ordem = interesse.ordem_compra

        assert ordem.itens.count() == 2
        item1 = ordem.itens.get(produto_nome="Pizza Margherita")
        assert item1.variacao_info == "Tamanho: Grande"
        assert item1.quantidade == 2
        assert item1.preco_unitario == Decimal("45.00")

    def test_criar_ordem_interesse_nao_convertido_erro(self):
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.criar_ordem_de_interesse(interesse)

        assert "CONVERTIDO" in str(exc_info.value)

    def test_criar_ordem_duplicada_erro(self):
        """Testa que não é possível criar ordem duplicada."""
        # Criar interesse como NOVO
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        # Converter (signal cria a ordem)
        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        # Tentar criar manualmente deve falhar
        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.criar_ordem_de_interesse(interesse)

        assert "já possui" in str(exc_info.value)


@pytest.mark.django_db
class TestOrdemCompraServiceAprovar:
    def test_aprovar_sucesso(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        usuario = UserFactory()

        ordem = OrdemCompraService.aprovar(ordem, usuario)

        assert ordem.status == StatusOrdemCompra.APROVADA
        assert ordem.aprovado_por == usuario
        assert ordem.data_aprovacao is not None

    def test_aprovar_ordem_ja_aprovada_erro(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        usuario = UserFactory()

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.aprovar(ordem, usuario)

        assert "não pode ser aprovada" in str(exc_info.value)


@pytest.mark.django_db
class TestOrdemCompraServiceRejeitar:
    def test_rejeitar_sucesso(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        usuario = UserFactory()

        ordem = OrdemCompraService.rejeitar(ordem, usuario, "Cliente desistiu")

        assert ordem.status == StatusOrdemCompra.REJEITADA
        assert ordem.aprovado_por == usuario
        assert ordem.motivo_rejeicao == "Cliente desistiu"

    def test_rejeitar_sem_motivo_erro(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        usuario = UserFactory()

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.rejeitar(ordem, usuario, "")

        assert "motivo" in str(exc_info.value).lower()

    def test_rejeitar_ordem_ja_aprovada_erro(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        usuario = UserFactory()

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.rejeitar(ordem, usuario, "Motivo")

        assert "não pode ser rejeitada" in str(exc_info.value)


@pytest.mark.django_db
class TestOrdemCompraServiceFaturar:
    def test_faturar_sucesso(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)

        ordem = OrdemCompraService.faturar(ordem)

        assert ordem.status == StatusOrdemCompra.FATURADA

    def test_faturar_ordem_nao_aprovada_erro(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.faturar(ordem)

        assert "não pode ser faturada" in str(exc_info.value)


@pytest.mark.django_db
class TestOrdemCompraServiceCancelar:
    def test_cancelar_ordem_pendente(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)

        ordem = OrdemCompraService.cancelar(ordem, "Cliente cancelou")

        assert ordem.status == StatusOrdemCompra.CANCELADA
        assert "Cliente cancelou" in ordem.observacoes

    def test_cancelar_ordem_aprovada(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)

        ordem = OrdemCompraService.cancelar(ordem)

        assert ordem.status == StatusOrdemCompra.CANCELADA

    def test_cancelar_ordem_faturada_erro(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.FATURADA)

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.cancelar(ordem)

        assert "não pode ser cancelada" in str(exc_info.value)


@pytest.mark.django_db
class TestOrdemCompraServiceConcluir:
    def test_concluir_sucesso(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.FATURADA)

        ordem = OrdemCompraService.concluir(ordem)

        assert ordem.status == StatusOrdemCompra.CONCLUIDA

    def test_concluir_ordem_nao_faturada_erro(self):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)

        with pytest.raises(OrdemCompraServiceError) as exc_info:
            OrdemCompraService.concluir(ordem)

        assert "não pode ser concluída" in str(exc_info.value)


@pytest.mark.django_db
class TestSignalCriarOrdemAoConverter:
    def test_signal_cria_ordem_ao_converter(self):
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        ItemInteresseFactory(interesse=interesse)

        # Mudar para convertido deve disparar o signal
        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        assert hasattr(interesse, "ordem_compra")
        assert interesse.ordem_compra.status == StatusOrdemCompra.PENDENTE_APROVACAO

    def test_signal_nao_duplica_ordem(self):
        interesse = InteresseCompraFactory(status=StatusInteresse.CONVERTIDO)
        ItemInteresseFactory(interesse=interesse)

        # Primeira vez cria
        assert OrdemCompra.objects.filter(interesse=interesse).count() == 1

        # Salvar novamente não deve duplicar
        interesse.save()
        assert OrdemCompra.objects.filter(interesse=interesse).count() == 1

    def test_signal_nao_cria_para_outros_status(self):
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)

        assert not OrdemCompra.objects.filter(interesse=interesse).exists()


@pytest.mark.django_db
class TestOrdemCompraServiceVinculaProdutos:
    """Testes para validar a vinculação automática de produtos ao criar ordem."""

    def test_criar_ordem_vincula_produto_existente(self):
        """Testa que o produto é vinculado quando existe no banco."""
        # Criar produto real
        produto = ProdutoFactory(produto="Camisa Polo")

        # Criar interesse com item que tem o mesmo nome do produto
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Camisa Polo",
            quantidade=1,
            preco_unitario=Decimal("99.00"),
        )

        # Converter dispara criação da ordem
        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        # Verificar vinculação
        item_ordem = interesse.ordem_compra.itens.first()
        assert item_ordem.produto == produto
        assert item_ordem.variacao is None

    def test_criar_ordem_vincula_variacao_existente(self):
        """Testa que a variação é vinculada quando existe no banco."""
        # Criar produto com variação
        produto = ProdutoFactory(produto="Camiseta Básica")
        atributo_cor = AtributoFactory(nome="Cor")
        atributo_tamanho = AtributoFactory(nome="Tamanho")
        valor_azul = ValorAtributoFactory(atributo=atributo_cor, valor="Azul")
        valor_m = ValorAtributoFactory(atributo=atributo_tamanho, valor="M")

        variacao = VariacaoProdutoFactory(produto=produto)
        variacao.valores.set([valor_azul, valor_m])

        # Criar interesse com item que corresponde à variação
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Camiseta Básica",
            variacao_info="Cor: Azul, Tamanho: M",
            quantidade=2,
            preco_unitario=Decimal("59.00"),
        )

        # Converter
        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        # Verificar vinculação
        item_ordem = interesse.ordem_compra.itens.first()
        assert item_ordem.produto == produto
        assert item_ordem.variacao == variacao

    def test_criar_ordem_produto_nao_encontrado_fica_null(self):
        """Testa que produto fica None se não existir no banco."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Produto Inexistente",
            quantidade=1,
            preco_unitario=Decimal("10.00"),
        )

        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        item_ordem = interesse.ordem_compra.itens.first()
        assert item_ordem.produto is None
        assert item_ordem.variacao is None
        assert item_ordem.produto_nome == "Produto Inexistente"

    def test_criar_ordem_variacao_nao_encontrada_vincula_so_produto(self):
        """Testa que só produto é vinculado se variação não corresponder."""
        produto = ProdutoFactory(produto="Tênis Runner")
        # Não criar variação

        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Tênis Runner",
            variacao_info="Cor: Verde, Tamanho: 42",  # Variação não existe
            quantidade=1,
            preco_unitario=Decimal("199.00"),
        )

        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        item_ordem = interesse.ordem_compra.itens.first()
        assert item_ordem.produto == produto
        assert item_ordem.variacao is None
