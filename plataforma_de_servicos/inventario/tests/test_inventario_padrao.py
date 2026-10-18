import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError
from plataforma_de_servicos.inventario.migrations_utils import marcar_padroes
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory

pytestmark = pytest.mark.django_db


def test_padrao_da_empresa_devolve_o_deposito_marcado():
    empresa = EmpresaFactory()
    InventarioFactory(nome="Secundário", empresa=empresa)
    padrao = InventarioFactory(nome="Principal", empresa=empresa, padrao=True)
    assert Inventario.objects.padrao_da_empresa(empresa) == padrao


def test_padrao_da_empresa_ignora_outras_empresas():
    empresa_a, empresa_b = EmpresaFactory(), EmpresaFactory()
    InventarioFactory(nome="B", empresa=empresa_b, padrao=True)
    with pytest.raises(InventarioPadraoAusenteError):
        Inventario.objects.padrao_da_empresa(empresa_a)


def test_so_um_padrao_por_empresa():
    empresa = EmpresaFactory()
    InventarioFactory(nome="Um", empresa=empresa, padrao=True)
    with pytest.raises(IntegrityError):
        InventarioFactory(nome="Dois", empresa=empresa, padrao=True)


def test_empresas_diferentes_podem_ter_cada_uma_seu_padrao():
    InventarioFactory(nome="A", empresa=EmpresaFactory(), padrao=True)
    InventarioFactory(nome="B", empresa=EmpresaFactory(), padrao=True)
    assert Inventario.objects.filter(padrao=True).count() == 2


def test_padrao_precisa_estar_ativo():
    inv = InventarioFactory.build(nome="Inativo", empresa=EmpresaFactory(), padrao=True, is_ativo=False)
    with pytest.raises(ValidationError):
        inv.clean()


def test_marcar_padroes_prefere_vitrine_mais_antigo():
    empresa = EmpresaFactory()
    InventarioFactory(nome="Depósito", empresa=empresa)
    vitrine = InventarioFactory(nome="Loja", empresa=empresa, exibir_na_vitrine=True)
    marcar_padroes(Inventario)
    vitrine.refresh_from_db()
    assert vitrine.padrao


def test_marcar_padroes_sem_vitrine_usa_ativo_mais_antigo():
    empresa = EmpresaFactory()
    antigo = InventarioFactory(nome="Antigo", empresa=empresa)
    InventarioFactory(nome="Novo", empresa=empresa)
    marcar_padroes(Inventario)
    antigo.refresh_from_db()
    assert antigo.padrao


def test_marcar_padroes_nao_mexe_em_empresa_que_ja_tem():
    empresa = EmpresaFactory()
    atual = InventarioFactory(nome="Atual", empresa=empresa, padrao=True)
    InventarioFactory(nome="Vitrine", empresa=empresa, exibir_na_vitrine=True)
    marcar_padroes(Inventario)
    assert list(Inventario.objects.filter(empresa=empresa, padrao=True)) == [atual]


def test_marcar_padroes_ignora_empresa_sem_ativo():
    empresa = EmpresaFactory()
    InventarioFactory(nome="Fechado", empresa=empresa, is_ativo=False)
    marcar_padroes(Inventario)
    assert not Inventario.objects.filter(empresa=empresa, padrao=True).exists()
