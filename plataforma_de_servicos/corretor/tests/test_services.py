from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail

from plataforma_de_servicos.corretor.services import enviar_notificacao_interesse
from plataforma_de_servicos.corretor.services import get_corretores_ativos_emails
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory

from .factories import InteresseCompraFactory
from .factories import ItemInteresseFactory

pytestmark = [pytest.mark.django_db]


class TestGetCorretoresAtivosEmails:
    """Testes para a função get_corretores_ativos_emails."""

    def test_retorna_emails_corretores_ativos(self):
        """Deve retornar apenas e-mails de funcionários corretores ativos."""
        user1 = UserFactory(email="ativo1@email.com")
        user2 = UserFactory(email="ativo2@email.com")
        user3 = UserFactory(email="inativo@email.com")

        FuncionarioFactory(usuario=user1, is_corretor=True, ativo=True)
        FuncionarioFactory(usuario=user2, is_corretor=True, ativo=True)
        FuncionarioFactory(usuario=user3, is_corretor=True, ativo=False)

        emails = get_corretores_ativos_emails()

        assert len(emails) == 2
        assert "ativo1@email.com" in emails
        assert "ativo2@email.com" in emails
        assert "inativo@email.com" not in emails

    def test_retorna_lista_vazia_sem_corretores(self):
        """Deve retornar lista vazia se não houver corretores."""
        emails = get_corretores_ativos_emails()
        assert emails == []

    def test_retorna_lista_vazia_todos_inativos(self):
        """Deve retornar lista vazia se todos estiverem inativos."""
        FuncionarioFactory(is_corretor=True, ativo=False)
        FuncionarioFactory(is_corretor=True, ativo=False)

        emails = get_corretores_ativos_emails()
        assert emails == []


class TestEnviarNotificacaoInteresse:
    """Testes para a função enviar_notificacao_interesse."""

    def test_interesse_nao_encontrado(self):
        """Deve retornar erro se interesse não existir."""
        resultado = enviar_notificacao_interesse(99999)

        assert resultado["success"] is False
        assert "não encontrado" in resultado["error"]

    def test_sem_corretores_ativos(self):
        """Deve retornar sucesso com 0 enviados se não houver corretores."""
        interesse = InteresseCompraFactory()

        resultado = enviar_notificacao_interesse(interesse.pk)

        assert resultado["success"] is True
        assert resultado["enviados"] == 0
        assert "Nenhum corretor ativo" in resultado["motivo"]

    def test_envia_email_para_corretores(self):
        """Deve enviar e-mail para todos os corretores ativos."""
        user1 = UserFactory(email="corretor1@email.com")
        user2 = UserFactory(email="corretor2@email.com")
        FuncionarioFactory(usuario=user1, is_corretor=True, ativo=True)
        FuncionarioFactory(usuario=user2, is_corretor=True, ativo=True)

        interesse = InteresseCompraFactory(
            nome_cliente="João Silva",
            email_cliente="joao@email.com",
            valor_total=Decimal("150.00"),
        )
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Pizza Margherita",
            quantidade=2,
            preco_unitario=Decimal("45.00"),
        )

        resultado = enviar_notificacao_interesse(interesse.pk)

        assert resultado["success"] is True
        assert resultado["enviados"] == 1  # send_mail retorna 1 por chamada
        assert len(mail.outbox) == 1

        # Verificar conteúdo do e-mail
        email_enviado = mail.outbox[0]
        assert f"#{interesse.pk}" in email_enviado.subject
        assert "João Silva" in email_enviado.subject
        assert "corretor1@email.com" in email_enviado.to
        assert "corretor2@email.com" in email_enviado.to

    def test_email_contem_dados_cliente(self):
        """E-mail deve conter dados do cliente."""
        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)

        interesse = InteresseCompraFactory(
            nome_cliente="Maria Santos",
            email_cliente="maria@email.com",
            telefone_cliente="11999998888",
        )

        enviar_notificacao_interesse(interesse.pk)

        email_enviado = mail.outbox[0]
        # Verificar no corpo texto
        assert "Maria Santos" in email_enviado.body
        assert "maria@email.com" in email_enviado.body
        assert "11999998888" in email_enviado.body

    def test_email_contem_produtos(self):
        """E-mail deve conter lista de produtos."""
        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)

        interesse = InteresseCompraFactory(valor_total=Decimal("100.00"))
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Pizza Calabresa",
            variacao_info="Tamanho: Grande",
            quantidade=1,
            preco_unitario=Decimal("50.00"),
        )
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Refrigerante",
            quantidade=2,
            preco_unitario=Decimal("25.00"),
        )

        enviar_notificacao_interesse(interesse.pk)

        email_enviado = mail.outbox[0]
        assert "Pizza Calabresa" in email_enviado.body
        assert "Refrigerante" in email_enviado.body
        assert "Tamanho: Grande" in email_enviado.body

    def test_email_contem_valor_total(self):
        """E-mail deve conter valor total."""
        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)

        interesse = InteresseCompraFactory(valor_total=Decimal("199.90"))

        enviar_notificacao_interesse(interesse.pk)

        email_enviado = mail.outbox[0]
        assert "199.90" in email_enviado.body or "199,90" in email_enviado.body

    def test_email_html_e_texto(self):
        """E-mail deve ter versão HTML e texto."""
        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)
        interesse = InteresseCompraFactory()

        enviar_notificacao_interesse(interesse.pk)

        email_enviado = mail.outbox[0]
        # Deve ter corpo texto
        assert email_enviado.body
        # Deve ter alternativa HTML
        assert len(email_enviado.alternatives) > 0
        html_content = email_enviado.alternatives[0][0]
        assert "<html" in html_content.lower()

    @patch("plataforma_de_servicos.corretor.services.send_mail")
    def test_erro_no_envio(self, mock_send_mail):
        """Deve tratar erro no envio de e-mail."""
        mock_send_mail.side_effect = Exception("SMTP Error")

        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)
        interesse = InteresseCompraFactory()

        resultado = enviar_notificacao_interesse(interesse.pk)

        assert resultado["success"] is False
        assert "SMTP Error" in resultado["error"]
