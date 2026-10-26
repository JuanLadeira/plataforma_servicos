import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.admin.ordem_compra_admin import OrdemCompraAdmin
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    EstoqueInsuficienteError,
)
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraServiceError,
)
from plataforma_de_servicos.vendas.tests.cenarios import ordem_com_itens

pytestmark = pytest.mark.django_db


def _nada_gravado(ordem):
    ordem.refresh_from_db()
    assert ordem.status == StatusOrdemCompra.PENDENTE_APROVACAO
    assert not Estoque.objects.filter(ordem_compra=ordem).exists()
    assert not Comissao.objects.filter(ordem=ordem).exists()


def test_baixa_sai_do_deposito_padrao_da_empresa_da_ordem(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(v, 2)])
    # depósito de outra empresa criado depois: era o que Inventario.objects.first() pegava
    outra = cenarios.deposito(empresa=EmpresaFactory(), nome="Outra", padrao=True)
    cenarios.variacao_com_saldo({outra: 50})

    OrdemCompraService.aprovar(ordem, usuario)

    saida = Estoque.objects.get(ordem_compra=ordem)
    assert saida.inventario_origem == padrao
    assert saida.processado
    assert cenarios.saldos(v, padrao) == (3, 3, 3)


def test_aprovar_com_corretor_cria_uma_comissao(empresa, padrao, usuario):
    produto = cenarios.produto_com_saldo({padrao: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(produto, 1)], com_corretor=True)
    OrdemCompraService.aprovar(ordem, usuario)
    assert Comissao.objects.filter(ordem=ordem).count() == 1


def test_empresa_sem_padrao_nao_aprova_e_nao_grava_nada(empresa, usuario):
    deposito = cenarios.deposito(empresa=empresa)
    produto = cenarios.produto_com_saldo({deposito: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(produto, 1)], com_corretor=True)
    with pytest.raises(OrdemCompraServiceError, match="depósito padrão"):
        OrdemCompraService.aprovar(ordem, usuario)
    _nada_gravado(ordem)


def test_saldo_insuficiente_no_padrao_vira_erro_de_estoque_e_desfaz_tudo(
    empresa, padrao, usuario
):
    outro = cenarios.deposito(empresa=empresa, nome="Secundário")
    v = cenarios.variacao_com_saldo({padrao: 1, outro: 9}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(v, 3)], com_corretor=True)
    with pytest.raises(EstoqueInsuficienteError, match="Principal"):
        OrdemCompraService.aprovar(ordem, usuario)
    _nada_gravado(ordem)
    assert cenarios.saldos(v, padrao) == (10, 10, 1)


def test_validar_estoque_usa_o_saldo_do_deposito_padrao(empresa, padrao):
    outro = cenarios.deposito(empresa=empresa, nome="Secundário")
    v = cenarios.variacao_com_saldo({padrao: 1, outro: 9}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(v, 3)])
    resultado = OrdemCompraService.validar_estoque(ordem)
    assert not resultado.is_valid
    assert resultado.items[0].quantidade_disponivel == 1


def test_validar_estoque_sem_padrao_e_invalido_sem_levantar(empresa):
    produto = cenarios.produto_com_saldo(
        {cenarios.deposito(empresa=empresa): 5}, empresa=empresa
    )
    ordem = ordem_com_itens(empresa, [(produto, 1)])
    resultado = OrdemCompraService.validar_estoque(ordem)
    assert not resultado.is_valid
    assert "depósito padrão" in resultado.message


def test_criar_ordem_manual_valida_pelo_deposito_padrao(empresa, padrao):
    outro = cenarios.deposito(empresa=empresa, nome="Secundário")
    produto = cenarios.produto_com_saldo({padrao: 1, outro: 9}, empresa=empresa)
    with pytest.raises(EstoqueInsuficienteError):
        OrdemCompraService.criar_ordem_manual(
            empresa=empresa,
            nome_cliente="Cliente",
            itens=[{"produto_id": produto.pk, "quantidade": 3, "preco_unitario": 10}],
        )


def test_criar_ordem_manual_sem_padrao_com_validacao_falha(empresa):
    produto = cenarios.produto_com_saldo(
        {cenarios.deposito(empresa=empresa): 5}, empresa=empresa
    )
    with pytest.raises(OrdemCompraServiceError, match="depósito padrão"):
        OrdemCompraService.criar_ordem_manual(
            empresa=empresa,
            nome_cliente="Cliente",
            itens=[{"produto_id": produto.pk, "quantidade": 1, "preco_unitario": 10}],
        )


def test_admin_mostra_mensagem_de_erro_em_vez_de_500(empresa, padrao, monkeypatch):
    produto = cenarios.produto_com_saldo({padrao: 1}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(produto, 2)])
    admin = OrdemCompraAdmin(OrdemCompra, AdminSite())
    mensagens = []
    monkeypatch.setattr(
        admin,
        "message_user",
        lambda request, msg, level=None, **kw: mensagens.append(msg),
    )
    request = RequestFactory().post("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)

    admin.action_aprovar(request, OrdemCompra.objects.filter(pk=ordem.pk))

    assert any("Saldo insuficiente" in m for m in mensagens), mensagens
    _nada_gravado(ordem)


def test_deposito_padrao_inativo_nao_conta(empresa, usuario):
    deposito = cenarios.deposito(empresa=empresa)
    Inventario.objects.filter(pk=deposito.pk).update(padrao=True, is_ativo=False)
    produto = cenarios.produto_com_saldo({deposito: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(produto, 1)])
    with pytest.raises(OrdemCompraServiceError, match="depósito padrão"):
        OrdemCompraService.aprovar(ordem, usuario)
