from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory

from .factories import InteresseCompraFactory

pytestmark = [pytest.mark.django_db]


class TestInteresseCompraView:
    """Testes para a view de demonstração de interesse."""

    def test_interesse_view_carrinho_vazio_redireciona(self, client):
        """Com carrinho vazio, deve redirecionar para o carrinho."""
        url = reverse("corretor:interesse-compra")
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("cart:cart-summary")

    def test_interesse_view_com_carrinho_get(self, client):
        """Com itens no carrinho, deve exibir o formulário."""
        # Criar produto e adicionar ao carrinho
        produto = ProdutoFactory(preco=Decimal("50.00"), estoque=10, empresa=EmpresaFactory())

        # Adicionar ao carrinho via session
        session = client.session
        session[f"cart_{produto.empresa.slug}"] = {
            f"produto_{produto.id}": {
                "qty": 2,
                "preco": "50.00",
            }
        }
        session.save()
        client.defaults["HTTP_HOST"] = f"{produto.empresa.slug}.localhost"

        url = reverse("corretor:interesse-compra")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert "cart" in response.context

    def test_interesse_view_post_sucesso(self, client):
        """POST com dados válidos deve criar interesse e redirecionar."""
        # Criar produto e adicionar ao carrinho
        produto = ProdutoFactory(preco=Decimal("50.00"), estoque=10, empresa=EmpresaFactory())

        session = client.session
        session[f"cart_{produto.empresa.slug}"] = {
            f"produto_{produto.id}": {
                "qty": 2,
                "preco": "50.00",
            }
        }
        session.save()
        client.defaults["HTTP_HOST"] = f"{produto.empresa.slug}.localhost"

        url = reverse("corretor:interesse-compra")
        data = {
            "nome_cliente": "João Silva",
            "email_cliente": "joao@email.com",
            "telefone_cliente": "11999999999",
            "mensagem": "Gostaria de mais informações",
        }
        response = client.post(url, data)

        # Verificar que o interesse foi criado
        assert InteresseCompra.objects.count() == 1
        interesse = InteresseCompra.objects.first()
        assert interesse.nome_cliente == "João Silva"
        assert interesse.email_cliente == "joao@email.com"
        assert interesse.valor_total == Decimal("100.00")  # 2 x 50.00

        # Verificar redirecionamento
        assert response.status_code == 302
        assert response.url == reverse("corretor:interesse-sucesso", args=[interesse.pk])

    def test_interesse_view_post_cria_itens(self, client):
        """POST deve criar os itens do interesse baseados no carrinho."""
        produto = ProdutoFactory(produto="Pizza Teste", preco=Decimal("45.00"), estoque=10, empresa=EmpresaFactory())

        session = client.session
        session[f"cart_{produto.empresa.slug}"] = {
            f"produto_{produto.id}": {
                "qty": 3,
                "preco": "45.00",
            }
        }
        session.save()
        client.defaults["HTTP_HOST"] = f"{produto.empresa.slug}.localhost"

        url = reverse("corretor:interesse-compra")
        data = {
            "nome_cliente": "Maria Santos",
            "email_cliente": "maria@email.com",
            "telefone_cliente": "11888888888",
            "mensagem": "",
        }
        response = client.post(url, data)

        # Verificar itens
        interesse = InteresseCompra.objects.first()
        assert interesse.itens.count() == 1

        item = interesse.itens.first()
        assert item.produto_nome == "Pizza Teste"
        assert item.quantidade == 3
        assert item.preco_unitario == Decimal("45.00")

    def test_interesse_view_post_limpa_carrinho(self, client):
        """POST deve limpar o carrinho após criar o interesse."""
        produto = ProdutoFactory(preco=Decimal("50.00"), estoque=10, empresa=EmpresaFactory())

        session = client.session
        session[f"cart_{produto.empresa.slug}"] = {
            f"produto_{produto.id}": {
                "qty": 1,
                "preco": "50.00",
            }
        }
        session.save()
        client.defaults["HTTP_HOST"] = f"{produto.empresa.slug}.localhost"

        url = reverse("corretor:interesse-compra")
        data = {
            "nome_cliente": "Pedro Oliveira",
            "email_cliente": "pedro@email.com",
            "telefone_cliente": "11777777777",
            "mensagem": "",
        }
        client.post(url, data)

        # Verificar que o carrinho foi limpo
        session = client.session
        assert session.get("cart", {}) == {}

    def test_interesse_view_post_dados_invalidos(self, client):
        """POST com dados inválidos deve retornar erros."""
        produto = ProdutoFactory(preco=Decimal("50.00"), estoque=10, empresa=EmpresaFactory())

        session = client.session
        session[f"cart_{produto.empresa.slug}"] = {
            f"produto_{produto.id}": {
                "qty": 1,
                "preco": "50.00",
            }
        }
        session.save()
        client.defaults["HTTP_HOST"] = f"{produto.empresa.slug}.localhost"

        url = reverse("corretor:interesse-compra")
        data = {
            "nome_cliente": "",  # Campo obrigatório vazio
            "email_cliente": "email-invalido",  # Email inválido
            "telefone_cliente": "",  # Campo obrigatório vazio
        }
        response = client.post(url, data)

        # Não deve criar interesse
        assert InteresseCompra.objects.count() == 0
        assert response.status_code == 200


class TestInteresseSucessoView:
    """Testes para a view de sucesso."""

    def _client_do_criador(self, client, interesse):
        """Simula o visitante que acabou de criar o interesse."""
        session = client.session
        session["interesses_criados"] = [interesse.pk]
        session.save()
        client.defaults["HTTP_HOST"] = f"{interesse.empresa.slug}.localhost"
        return client

    def test_sucesso_view_interesse_existente(self, client):
        """Deve exibir os detalhes do interesse para quem o criou."""
        interesse = InteresseCompraFactory(nome_cliente="João Teste", empresa=EmpresaFactory())
        client = self._client_do_criador(client, interesse)

        url = reverse("corretor:interesse-sucesso", args=[interesse.pk])
        response = client.get(url)

        assert response.status_code == 200
        assert "interesse" in response.context
        assert response.context["interesse"] == interesse

    def test_sucesso_view_interesse_inexistente(self, client):
        """Interesse inexistente deve redirecionar para home."""
        url = reverse("corretor:interesse-sucesso", args=[99999])
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_sucesso_view_outro_visitante_nao_ve_dados(self, client):
        """Visitante que não criou o interesse não vê os dados do cliente."""
        interesse = InteresseCompraFactory(email_cliente="vitima@email.com", empresa=EmpresaFactory())

        url = reverse("corretor:interesse-sucesso", args=[interesse.pk])
        response = client.get(url, HTTP_HOST=f"{interesse.empresa.slug}.localhost")

        assert response.status_code == 302
        assert "vitima@email.com" not in response.content.decode()

    def test_sucesso_view_nao_mostra_interesse_de_outra_empresa(self, client):
        """Mesmo com o id na sessão, um interesse de outra empresa não aparece."""
        interesse = InteresseCompraFactory(email_cliente="vitima@email.com", empresa=EmpresaFactory())
        outro = InteresseCompraFactory(empresa=EmpresaFactory())
        assert outro.empresa != interesse.empresa
        client = self._client_do_criador(client, interesse)

        url = reverse("corretor:interesse-sucesso", args=[interesse.pk])
        response = client.get(url, HTTP_HOST=f"{outro.empresa.slug}.localhost")

        assert response.status_code == 302
        assert "vitima@email.com" not in response.content.decode()

    def test_sucesso_view_dominio_principal_nao_mostra(self, client):
        """No domínio principal (sem tenant) nenhum interesse é exibido."""
        interesse = InteresseCompraFactory(empresa=EmpresaFactory())
        session = client.session
        session["interesses_criados"] = [interesse.pk]
        session.save()

        url = reverse("corretor:interesse-sucesso", args=[interesse.pk])
        response = client.get(url, HTTP_HOST="localhost")

        assert response.status_code == 302

    def test_post_permite_ver_o_proprio_interesse(self, client):
        """Fluxo completo: quem cria o interesse vê a página de sucesso."""
        produto = ProdutoFactory(preco=Decimal("50.00"), estoque=10, empresa=EmpresaFactory())
        session = client.session
        session[f"cart_{produto.empresa.slug}"] = {
            f"produto_{produto.id}": {"qty": 1, "preco": "50.00"},
        }
        session.save()
        client.defaults["HTTP_HOST"] = f"{produto.empresa.slug}.localhost"

        response = client.post(
            reverse("corretor:interesse-compra"),
            {
                "nome_cliente": "Maria",
                "email_cliente": "maria@email.com",
                "telefone_cliente": "11999999999",
            },
            follow=True,
        )

        assert response.status_code == 200
        interesse = InteresseCompra.objects.get()
        assert interesse.empresa == produto.empresa
        assert response.context["interesse"] == interesse


class TestInteresseCompraSemTenant:
    """Checkout no domínio principal não pode criar interesse sem empresa."""

    def test_checkout_sem_tenant_retorna_404(self, client):
        produto = ProdutoFactory(preco=Decimal("50.00"), estoque=10, empresa=EmpresaFactory())
        session = client.session
        session["cart"] = {f"produto_{produto.id}": {"qty": 1, "preco": "50.00"}}
        session.save()

        response = client.post(
            reverse("corretor:interesse-compra"),
            {
                "nome_cliente": "Maria",
                "email_cliente": "maria@email.com",
                "telefone_cliente": "11999999999",
            },
            HTTP_HOST="localhost",
        )

        assert response.status_code == 404
        assert InteresseCompra.objects.count() == 0
