import pytest
from django.test import RequestFactory

from plataforma_de_servicos.core.admin.sites.gerente_admin_site import gerente_site
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.inventario.admin.gerente_admin import InventarioGerenteAdmin
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def model_admin():
    return InventarioGerenteAdmin(Inventario, gerente_site)


def _request(empresa):
    request = RequestFactory().post("/")
    request.user = UserFactory(is_staff=True, is_superuser=True)
    request.tenant = empresa
    return request


def test_marcar_novo_padrao_desmarca_o_anterior(model_admin):
    empresa = EmpresaFactory()
    antigo = InventarioFactory(nome="Antigo", empresa=empresa, padrao=True)
    novo = InventarioFactory(nome="Novo", empresa=empresa)
    novo.padrao = True
    model_admin.save_model(_request(empresa), novo, form=None, change=True)
    antigo.refresh_from_db()
    novo.refresh_from_db()
    assert novo.padrao
    assert not antigo.padrao


def test_criar_padrao_desmarca_o_anterior_da_empresa_do_tenant(model_admin):
    empresa = EmpresaFactory()
    antigo = InventarioFactory(nome="Antigo", empresa=empresa, padrao=True)
    novo = Inventario(nome="Novo", padrao=True)
    model_admin.save_model(_request(empresa), novo, form=None, change=False)
    antigo.refresh_from_db()
    assert novo.empresa == empresa
    assert novo.padrao
    assert not antigo.padrao


def test_padrao_de_outra_empresa_nao_e_desmarcado(model_admin):
    empresa_a, empresa_b = EmpresaFactory(), EmpresaFactory()
    outro = InventarioFactory(nome="B", empresa=empresa_b, padrao=True)
    novo = InventarioFactory(nome="A", empresa=empresa_a)
    novo.padrao = True
    model_admin.save_model(_request(empresa_a), novo, form=None, change=True)
    outro.refresh_from_db()
    assert outro.padrao


def test_padrao_aparece_na_listagem_e_no_formulario(model_admin):
    assert "padrao" in model_admin.list_display
    assert "padrao" in model_admin.list_filter
    campos = [c for _, opcoes in model_admin.fieldsets for c in opcoes["fields"]]
    assert "padrao" in campos
