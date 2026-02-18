from decimal import Decimal
from unittest.mock import patch

import pytest

from plataforma_de_servicos.corretor.tasks import notificar_corretores_novo_interesse
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory

from .factories import InteresseCompraFactory

pytestmark = [pytest.mark.django_db]


class TestNotificarCorretoresNovoInteresse:
    """Testes para a task notificar_corretores_novo_interesse."""

    def test_task_chama_servico(self):
        """Task deve chamar o serviço de envio."""
        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)
        interesse = InteresseCompraFactory()

        with patch(
            "plataforma_de_servicos.corretor.tasks.enviar_notificacao_interesse"
        ) as mock_enviar:
            mock_enviar.return_value = {"success": True, "enviados": 1}

            resultado = notificar_corretores_novo_interesse(interesse.pk)

            mock_enviar.assert_called_once_with(interesse.pk)
            assert resultado["success"] is True

    def test_task_retorna_resultado_servico(self):
        """Task deve retornar o resultado do serviço."""
        interesse = InteresseCompraFactory()

        with patch(
            "plataforma_de_servicos.corretor.tasks.enviar_notificacao_interesse"
        ) as mock_enviar:
            mock_enviar.return_value = {
                "success": True,
                "enviados": 3,
                "destinatarios": ["a@b.com", "c@d.com", "e@f.com"],
            }

            resultado = notificar_corretores_novo_interesse(interesse.pk)

            assert resultado["enviados"] == 3
            assert len(resultado["destinatarios"]) == 3

    def test_task_com_interesse_inexistente(self):
        """Task deve retornar erro para interesse inexistente."""
        with patch(
            "plataforma_de_servicos.corretor.tasks.enviar_notificacao_interesse"
        ) as mock_enviar:
            mock_enviar.return_value = {"success": False, "error": "Interesse não encontrado"}

            resultado = notificar_corretores_novo_interesse(99999)

            assert resultado["success"] is False

    def test_task_executa_sincrona(self):
        """Task deve funcionar quando executada de forma síncrona."""
        user = UserFactory(email="corretor@email.com")
        FuncionarioFactory(usuario=user, is_corretor=True, ativo=True)
        interesse = InteresseCompraFactory(valor_total=Decimal("100.00"))

        # Executar a task diretamente (síncrona)
        resultado = notificar_corretores_novo_interesse(interesse.pk)

        assert resultado["success"] is True
