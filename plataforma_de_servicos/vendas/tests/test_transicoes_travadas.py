import pytest

from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services.ordem_compra_service import OrdemCompraService
from plataforma_de_servicos.vendas.services.ordem_compra_service import OrdemCompraServiceError
from plataforma_de_servicos.vendas.tests.factories import OrdemCompraFactory

pytestmark = pytest.mark.django_db


def _executar(acao, ordem):
    if acao == "aprovar":
        return OrdemCompraService.aprovar(ordem, UserFactory())
    if acao == "rejeitar":
        return OrdemCompraService.rejeitar(ordem, UserFactory(), "motivo")
    return getattr(OrdemCompraService, acao)(ordem)


@pytest.mark.parametrize(
    ("acao", "status_inicial", "status_final"),
    [
        ("aprovar", StatusOrdemCompra.PENDENTE_APROVACAO, StatusOrdemCompra.APROVADA),
        ("rejeitar", StatusOrdemCompra.PENDENTE_APROVACAO, StatusOrdemCompra.REJEITADA),
        ("faturar", StatusOrdemCompra.APROVADA, StatusOrdemCompra.FATURADA),
        ("cancelar", StatusOrdemCompra.APROVADA, StatusOrdemCompra.CANCELADA),
        ("concluir", StatusOrdemCompra.FATURADA, StatusOrdemCompra.CONCLUIDA),
    ],
)
def test_transicao_checa_status_no_registro_travado(acao, status_inicial, status_final):
    a = OrdemCompraFactory(status=status_inicial)
    b = OrdemCompra.objects.get(pk=a.pk)  # instância antiga, como a de outro request
    resultado = _executar(acao, a)
    assert resultado.status == status_final
    assert a.status == status_final
    with pytest.raises(OrdemCompraServiceError):
        _executar(acao, b)
    assert OrdemCompra.objects.get(pk=a.pk).status == status_final


def test_cancelar_nao_perde_observacoes_gravadas_por_outro_request():
    a = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA, observacoes="")
    OrdemCompra.objects.filter(pk=a.pk).update(observacoes="Cliente pediu urgência")
    OrdemCompraService.cancelar(a, "desistiu")
    a.refresh_from_db()
    assert "Cliente pediu urgência" in a.observacoes
    assert "Cancelamento: desistiu" in a.observacoes
