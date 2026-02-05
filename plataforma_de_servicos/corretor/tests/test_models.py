import pytest
from django.db import IntegrityError

from plataforma_de_servicos.corretor.models import Corretor
from plataforma_de_servicos.users.tests.factories import UserFactory

from .factories import CorretorFactory

pytestmark = [pytest.mark.django_db]


class TestCorretorModel:
    """Testes para o modelo Corretor."""

    def test_criar_corretor_simples(self):
        """Deve criar um corretor com os campos básicos."""
        corretor = CorretorFactory(
            nome="João Silva",
            email="joao@email.com",
            telefone="11999999999",
        )

        assert corretor.pk is not None
        assert corretor.nome == "João Silva"
        assert corretor.email == "joao@email.com"
        assert corretor.telefone == "11999999999"
        assert corretor.ativo is True

    def test_corretor_str(self):
        """O __str__ deve retornar o nome do corretor."""
        corretor = CorretorFactory(nome="Maria Santos")
        assert str(corretor) == "Maria Santos"

    def test_corretor_com_usuario(self):
        """Deve associar um corretor a um usuário."""
        user = UserFactory()
        corretor = CorretorFactory(nome="Pedro Oliveira", user=user)

        assert corretor.user == user
        assert user.corretor == corretor

    def test_corretor_com_usuario_trait(self):
        """Deve criar corretor com usuário usando trait."""
        corretor = CorretorFactory(com_usuario=True)

        assert corretor.user is not None
        assert corretor.user.pk is not None

    def test_corretor_email_unico_por_empresa(self):
        """Email do corretor deve ser único dentro da mesma empresa."""
        from plataforma_de_servicos.empresa.models import Empresa

        # Criar duas empresas
        empresa1 = Empresa.objects.create(nome="Empresa 1", slug="empresa-1")
        empresa2 = Empresa.objects.create(nome="Empresa 2", slug="empresa-2")

        # Mesmo email em empresas diferentes deve funcionar
        CorretorFactory(email="unico@email.com", empresa=empresa1)
        corretor2 = CorretorFactory(email="unico@email.com", empresa=empresa2)
        assert corretor2.pk is not None

        # Mesmo email na mesma empresa deve falhar
        with pytest.raises(IntegrityError):
            CorretorFactory(email="unico@email.com", empresa=empresa1)

    def test_corretor_telefone_opcional(self):
        """Telefone deve ser opcional."""
        corretor = CorretorFactory(telefone="")
        assert corretor.telefone == ""

    def test_corretor_inativo(self):
        """Deve permitir criar corretor inativo."""
        corretor = CorretorFactory(ativo=False)
        assert corretor.ativo is False

    def test_corretor_timestamps(self):
        """Deve ter timestamps de criação e modificação."""
        corretor = CorretorFactory()

        assert corretor.created is not None
        assert corretor.modified is not None

    def test_corretor_ordering(self):
        """Corretores devem ser ordenados por nome."""
        CorretorFactory(nome="Zélia")
        CorretorFactory(nome="Ana")
        CorretorFactory(nome="Maria")

        corretores = list(Corretor.objects.values_list("nome", flat=True))
        assert corretores == ["Ana", "Maria", "Zélia"]

    def test_delete_user_mantem_corretor(self):
        """Deletar usuário deve manter o corretor (SET_NULL)."""
        user = UserFactory()
        corretor = CorretorFactory(user=user)
        corretor_id = corretor.pk

        user.delete()

        corretor.refresh_from_db()
        assert corretor.pk == corretor_id
        assert corretor.user is None

    def test_verbose_names(self):
        """Deve ter verbose names corretos."""
        assert Corretor._meta.verbose_name == "corretor"
        assert Corretor._meta.verbose_name_plural == "corretores"
