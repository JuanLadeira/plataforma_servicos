from decimal import Decimal

import pytest

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory

from .factories import InteresseCompraFactory
from .factories import ItemInteresseFactory

pytestmark = [pytest.mark.django_db]


class TestInteresseCompraModel:
    """Testes para o modelo InteresseCompra."""

    def test_criar_interesse_simples(self):
        """Deve criar um interesse com os campos básicos."""
        interesse = InteresseCompraFactory(
            nome_cliente="João Silva",
            email_cliente="joao@email.com",
            telefone_cliente="11999999999",
            valor_total=Decimal("150.00"),
        )

        assert interesse.pk is not None
        assert interesse.nome_cliente == "João Silva"
        assert interesse.email_cliente == "joao@email.com"
        assert interesse.telefone_cliente == "11999999999"
        assert interesse.valor_total == Decimal("150.00")
        assert interesse.status == StatusInteresse.NOVO

    def test_interesse_str(self):
        """O __str__ deve retornar o formato correto."""
        interesse = InteresseCompraFactory(nome_cliente="Maria Santos")
        assert f"Interesse #{interesse.pk} - Maria Santos" == str(interesse)

    def test_interesse_com_corretor(self):
        """Deve associar um interesse a um funcionário corretor."""
        funcionario = FuncionarioFactory(is_corretor=True)
        interesse = InteresseCompraFactory(corretor=funcionario)

        assert interesse.corretor == funcionario
        assert interesse in funcionario.interesses.all()

    def test_interesse_status_choices(self):
        """Deve aceitar todos os status válidos."""
        for status_choice in StatusInteresse.choices:
            interesse = InteresseCompraFactory(status=status_choice[0])
            assert interesse.status == status_choice[0]

    def test_interesse_timestamps(self):
        """Deve ter timestamps de criação e modificação."""
        interesse = InteresseCompraFactory()

        assert interesse.created is not None
        assert interesse.modified is not None

    def test_interesse_ordering(self):
        """Interesses devem ser ordenados por data de criação (mais recente primeiro)."""
        interesse1 = InteresseCompraFactory()
        interesse2 = InteresseCompraFactory()
        interesse3 = InteresseCompraFactory()

        interesses = list(InteresseCompra.objects.all())
        assert interesses[0] == interesse3
        assert interesses[1] == interesse2
        assert interesses[2] == interesse1

    def test_interesse_mensagem_opcional(self):
        """Mensagem deve ser opcional."""
        interesse = InteresseCompraFactory(mensagem="")
        assert interesse.mensagem == ""

    def test_verbose_names_interesse(self):
        """Deve ter verbose names corretos."""
        assert InteresseCompra._meta.verbose_name == "interesse de compra"
        assert InteresseCompra._meta.verbose_name_plural == "interesses de compra"


class TestItemInteresseModel:
    """Testes para o modelo ItemInteresse."""

    def test_criar_item_simples(self):
        """Deve criar um item com os campos básicos."""
        interesse = InteresseCompraFactory()
        item = ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Pizza Margherita",
            quantidade=2,
            preco_unitario=Decimal("45.00"),
        )

        assert item.pk is not None
        assert item.interesse == interesse
        assert item.produto_nome == "Pizza Margherita"
        assert item.quantidade == 2
        assert item.preco_unitario == Decimal("45.00")

    def test_item_str(self):
        """O __str__ deve retornar o formato correto."""
        item = ItemInteresseFactory(quantidade=3, produto_nome="Pizza Calabresa")
        assert str(item) == "3x Pizza Calabresa"

    def test_item_subtotal(self):
        """Deve calcular o subtotal corretamente."""
        item = ItemInteresseFactory(
            quantidade=2,
            preco_unitario=Decimal("45.00"),
        )
        assert item.subtotal == Decimal("90.00")

    def test_item_com_variacao_info(self):
        """Deve aceitar informações de variação."""
        item = ItemInteresseFactory(
            produto_nome="Camiseta",
            variacao_info="Cor: Azul, Tamanho: M",
        )
        assert item.variacao_info == "Cor: Azul, Tamanho: M"

    def test_item_cascade_delete(self):
        """Deletar interesse deve deletar os itens."""
        interesse = InteresseCompraFactory()
        ItemInteresseFactory(interesse=interesse)
        ItemInteresseFactory(interesse=interesse)

        assert ItemInteresse.objects.filter(interesse=interesse).count() == 2

        interesse.delete()

        assert ItemInteresse.objects.filter(interesse_id=interesse.pk).count() == 0

    def test_interesse_com_multiplos_itens(self):
        """Deve permitir múltiplos itens por interesse."""
        interesse = InteresseCompraFactory()
        item1 = ItemInteresseFactory(interesse=interesse, produto_nome="Pizza 1")
        item2 = ItemInteresseFactory(interesse=interesse, produto_nome="Pizza 2")
        item3 = ItemInteresseFactory(interesse=interesse, produto_nome="Refrigerante")

        assert interesse.itens.count() == 3
        assert item1 in interesse.itens.all()
        assert item2 in interesse.itens.all()
        assert item3 in interesse.itens.all()

    def test_verbose_names_item(self):
        """Deve ter verbose names corretos."""
        assert ItemInteresse._meta.verbose_name == "item do interesse"
        assert ItemInteresse._meta.verbose_name_plural == "itens do interesse"
