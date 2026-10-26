import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from plataforma_de_servicos.core.admin.sites.gerente_admin_site import gerente_site
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.admin import ordem_compra_admin
from plataforma_de_servicos.vendas.admin.ordem_compra_admin import OrdemCompraAdmin
from plataforma_de_servicos.vendas.admin.ordem_compra_admin import (
    OrdemCompraGerenteAdmin,
)
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services.commission_service import CommissionService
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)
from plataforma_de_servicos.vendas.tests.cenarios import ordem_com_itens

pytestmark = pytest.mark.django_db


@pytest.fixture
def gerente():
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def admin(monkeypatch):
    admin = OrdemCompraGerenteAdmin(OrdemCompra, gerente_site)
    admin.mensagens = []
    monkeypatch.setattr(
        admin,
        "message_user",
        lambda request, msg, level=None, **kw: admin.mensagens.append(msg),
    )
    return admin


@pytest.fixture
def aprovada(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(v, 2)], com_corretor=True)
    return OrdemCompraService.aprovar(ordem, usuario), v


def _request(metodo, empresa, user, data=None):
    request = getattr(RequestFactory(), metodo)("/", data or {})
    request.user = user
    request.tenant = empresa
    request.session = {}
    return request


def test_status_somente_leitura_no_admin_principal(empresa):
    ordem = ordem_com_itens(empresa, [])
    admin = OrdemCompraAdmin(OrdemCompra, AdminSite())
    request = _request("get", None, UserFactory(is_staff=True, is_superuser=True))

    campos = admin.get_readonly_fields(request, ordem)

    assert {"status", "cancelado_por", "data_cancelamento"} <= set(campos)


def test_detail_cancelar_registra_usuario_e_devolve_estoque(
    admin, aprovada, empresa, padrao, gerente
):
    ordem, v = aprovada

    admin.detail_cancelar(
        _request("post", empresa, gerente, {"motivo": "desistiu"}), object_id=ordem.pk
    )

    ordem.refresh_from_db()
    assert ordem.status == StatusOrdemCompra.CANCELADA
    assert ordem.cancelado_por == gerente
    assert cenarios.saldos(v, padrao) == (5, 5, 5)


def test_detail_cancelar_com_comissao_paga_mostra_erro(
    admin, aprovada, empresa, gerente, monkeypatch
):
    ordem, _ = aprovada
    comissao = Comissao.objects.get(ordem=ordem)
    CommissionService(empresa).aprovar_comissao(comissao)
    CommissionService(empresa).pagar_comissao(comissao)
    monkeypatch.setattr(
        ordem_compra_admin, "render", lambda request, template, context: context
    )

    admin.detail_cancelar(
        _request("post", empresa, gerente, {"motivo": "teste"}), object_id=ordem.pk
    )

    ordem.refresh_from_db()
    assert ordem.status == StatusOrdemCompra.APROVADA
    assert any("já paga" in m for m in admin.mensagens), admin.mensagens


def test_tela_de_cancelamento_mostra_o_que_sera_estornado(
    admin, aprovada, empresa, padrao, gerente, monkeypatch
):
    ordem, v = aprovada
    monkeypatch.setattr(
        ordem_compra_admin, "render", lambda request, template, context: context
    )

    contexto = admin.detail_cancelar(
        _request("get", empresa, gerente), object_id=ordem.pk
    )

    [saida] = contexto["saidas_a_estornar"]
    assert saida.inventario_origem == padrao
    assert [i.quantidade for i in saida.estoque_itens.all()] == [2]
    [comissao] = contexto["comissoes_a_cancelar"]
    assert comissao.ordem_id == ordem.pk
    assert contexto["comissao_paga"] is False


def test_tela_de_cancelamento_renderiza_o_resumo(aprovada, empresa, padrao, client):
    ordem, _ = aprovada
    gerente = UserFactory(is_staff=True, is_superuser=True)
    client.force_login(gerente)

    resposta = client.get(
        f"/gerentes/vendas/ordemcompra/{ordem.pk}/cancelar/", {"tenant": empresa.slug}
    )

    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert "O que será desfeito" in conteudo
    assert "voltam ao depósito Principal" in conteudo
