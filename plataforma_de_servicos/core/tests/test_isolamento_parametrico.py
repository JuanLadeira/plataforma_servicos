"""
Teste paramétrico de isolamento entre empresas.

Cria o mesmo conjunto completo de dados em duas empresas (A e B) e percorre
automaticamente todos os ModelAdmins registrados nos portais de gerentes e
vendedores, além das views públicas e das APIs de estoque. Em nenhum caso um
funcionário da empresa A pode ver ou abrir um objeto da empresa B.

Ao registrar um novo model num portal, adicione em EMPRESA_PATH o caminho do
model até a empresa; o teste falha enquanto o caminho não existir.
"""

from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from plataforma_de_servicos.core.admin.sites.gerente_admin_site import gerente_site
from plataforma_de_servicos.core.admin.sites.vendedor_admin_site import vendedor_site
from plataforma_de_servicos.core.models import SiteConfig
from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.corretor.tests.factories import ItemInteresseFactory
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.models.estoque_model import Estoque
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.inventario.tests.factories import InventarioSaldoFactory
from plataforma_de_servicos.produto.tests.factories import AtributoFactory
from plataforma_de_servicos.produto.tests.factories import CategoriaFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import ValorAtributoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory
from plataforma_de_servicos.users.models import PapelFuncionario
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import ConfiguracaoComissao
from plataforma_de_servicos.vendas.tests.factories import OrdemCompraFactory

pytestmark = [pytest.mark.django_db]

# Caminho de cada model registrado nos portais até a Empresa dona do registro.
EMPRESA_PATH = {
    "produto.Produto": "empresa",
    "produto.Categoria": "empresa",
    "produto.Atributo": "categoria__empresa",
    "produto.ValorAtributo": "atributo__categoria__empresa",
    "produto.VariacaoProduto": "produto__empresa",
    "estoque.EstoqueEntrada": "empresa",
    "estoque.EstoqueSaida": "empresa",
    "estoque.Transferencia": "empresa",
    "inventario.Inventario": "empresa",
    "corretor.InteresseCompra": "empresa",
    "vendas.OrdemCompra": "empresa",
    "vendas.Comissao": "empresa",
    "vendas.ConfiguracaoComissao": "empresa",
    "users.User": "empresa",
    "users.Funcionario": "empresa",
    "core.SiteConfig": "empresa",
}

SITES = {"gerentes": gerente_site, "vendedores": vendedor_site}


def _models(site):
    return list(site._registry)  # noqa: SLF001


ADMIN_CASES = [
    pytest.param(site_name, model, id=f"{site_name}-{model._meta.label}")
    for site_name, site in SITES.items()
    for model in _models(site)
]

PAPEIS = [
    pytest.param(PapelFuncionario.GERENTE, id="gerente"),
    pytest.param(PapelFuncionario.VENDEDOR, id="vendedor"),
]

# Subdomínio da empresa A e domínio principal (tenant vem do usuário).
HOSTS = [
    pytest.param("empresaa.localhost", id="subdominio"),
    pytest.param("localhost", id="dominio-principal"),
]


def _criar_dados(empresa, tag):
    """Cria um registro de cada model dos portais para a empresa."""
    user = UserFactory(
        email=f"vendedor@{tag}.com", name=f"Vendedor {tag}", empresa=empresa
    )
    funcionario = FuncionarioFactory(
        usuario=user,
        empresa=empresa,
        papel=PapelFuncionario.VENDEDOR,
        is_corretor=True,
    )
    categoria = CategoriaFactory(categoria=f"Categoria {tag}", empresa=empresa)
    produto = ProdutoFactory(
        produto=f"Produto {tag}", empresa=empresa, categoria=categoria
    )
    atributo = AtributoFactory(nome=f"Atributo {tag}", categoria=categoria)
    valor = ValorAtributoFactory(atributo=atributo, valor=f"Valor {tag}")
    variacao = VariacaoProdutoFactory(produto=produto, valores=[valor])
    inventario = InventarioFactory(nome=f"Inventario {tag}", empresa=empresa)
    InventarioSaldoFactory(inventario=inventario, produto=produto, variacao=variacao)
    for movimento in ("e", "s", "t"):
        Estoque.objects.create(
            empresa=empresa,
            movimento=movimento,
            funcionario=user,
            nf=1,
            inventario_origem=inventario if movimento in ("s", "t") else None,
            inventario_destino=inventario if movimento in ("e", "t") else None,
        )
    interesse = InteresseCompraFactory(empresa=empresa, nome_cliente=f"Cliente {tag}")
    ItemInteresseFactory(interesse=interesse)
    ordem = OrdemCompraFactory(
        empresa=empresa,
        interesse=InteresseCompraFactory(empresa=empresa),
        corretor=funcionario,
    )
    Comissao.objects.create(
        empresa=empresa,
        ordem=ordem,
        funcionario=funcionario,
        percentual=Decimal("5.00"),
        valor_base=Decimal("100.00"),
        valor_comissao=Decimal("5.00"),
    )
    ConfiguracaoComissao.objects.get_or_create(empresa=empresa)
    SiteConfig.objects.get_or_create(empresa=empresa)
    return {
        "produto": produto,
        "variacao": variacao,
        "inventario": inventario,
        "interesse": interesse,
    }


@pytest.fixture
def empresas():
    empresa_a = EmpresaFactory(nome="Empresa A", slug="empresaa")
    empresa_b = EmpresaFactory(nome="Empresa B", slug="empresab")
    dados_a = _criar_dados(empresa_a, "empresaa")
    dados_b = _criar_dados(empresa_b, "empresab")
    return empresa_a, empresa_b, dados_a, dados_b


def _cliente(empresa, papel):
    """Funcionário da empresa com todas as permissões de model do Django.

    Assim o que impede o acesso é o isolamento por empresa, e não a falta de
    permissão do usuário.
    """
    user = UserFactory(empresa=empresa, is_staff=True)
    user.user_permissions.set(Permission.objects.all())
    FuncionarioFactory(usuario=user, empresa=empresa, papel=papel)
    client = Client()
    client.force_login(user)
    return client


def _objetos_da_empresa(model, empresa):
    return model._default_manager.filter(**{EMPRESA_PATH[model._meta.label]: empresa})


def _contexto(response):
    return (
        response.context_data
        if getattr(response, "context_data", None)
        else response.context
    )


def test_todo_model_dos_portais_tem_caminho_ate_empresa():
    sem_caminho = sorted(
        model._meta.label
        for site in SITES.values()
        for model in _models(site)
        if model._meta.label not in EMPRESA_PATH
    )
    assert not sem_caminho, f"Adicione em EMPRESA_PATH: {sem_caminho}"


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("papel", PAPEIS)
@pytest.mark.parametrize(("site_name", "model"), ADMIN_CASES)
def test_listagem_nao_mostra_objetos_da_outra_empresa(
    empresas, site_name, model, papel, host
):
    empresa_a, empresa_b, _, _ = empresas
    assert _objetos_da_empresa(model, empresa_b).exists(), (
        "dados da empresa B não foram criados"
    )

    url = reverse(
        f"{site_name}:{model._meta.app_label}_{model._meta.model_name}_changelist"
    )
    response = _cliente(empresa_a, papel).get(url, HTTP_HOST=host, follow=True)

    if response.status_code != 200:
        return  # sem acesso à listagem: nada vaza
    contexto = _contexto(response)
    path = EMPRESA_PATH[model._meta.label]
    if contexto and "cl" in contexto:
        vazados = contexto["cl"].queryset.filter(**{path: empresa_b})
        assert not vazados.exists(), (
            f"{model._meta.label} da empresa B na listagem: {list(vazados)}"
        )
    elif contexto and contexto.get("original") is not None:
        original = contexto["original"]
        assert not _objetos_da_empresa(model, empresa_b).filter(pk=original.pk).exists()


@pytest.mark.parametrize("view", ["change", "delete", "history"])
@pytest.mark.parametrize("papel", PAPEIS)
@pytest.mark.parametrize(("site_name", "model"), ADMIN_CASES)
def test_objeto_da_outra_empresa_nao_abre(empresas, site_name, model, papel, view):
    empresa_a, empresa_b, _, _ = empresas
    objeto_b = _objetos_da_empresa(model, empresa_b).first()

    url = reverse(
        f"{site_name}:{model._meta.app_label}_{model._meta.model_name}_{view}",
        args=[objeto_b.pk],
    )
    response = _cliente(empresa_a, papel).get(url, HTTP_HOST="localhost", follow=True)

    contexto = _contexto(response) or {}
    aberto = contexto.get("original") or contexto.get("object")
    assert not (
        response.status_code == 200 and aberto is not None and aberto.pk == objeto_b.pk
    ), f"{view} de {model._meta.label} da empresa B abriu para a empresa A"


@pytest.mark.parametrize("host", HOSTS)
def test_views_publicas_nao_abrem_itens_da_outra_empresa(empresas, host):
    _, _, _, dados_b = empresas
    client = Client()

    respostas = {
        "produto": client.get(
            reverse("produto-detail", args=[dados_b["produto"].slug]),
            HTTP_HOST=host,
        ),
        "variacao": client.get(
            reverse("variacao-detail", args=[dados_b["variacao"].sku]),
            HTTP_HOST=host,
        ),
        "preco": client.post(
            reverse("calcular-preco-variacao"),
            {"produto_id": dados_b["produto"].pk},
            HTTP_HOST=host,
        ),
        "lead": client.get(
            reverse("corretor:interesse-sucesso", args=[dados_b["interesse"].pk]),
            HTTP_HOST=host,
        ),
    }

    abertos = {
        nome: r.status_code for nome, r in respostas.items() if r.status_code == 200
    }
    assert not abertos, f"itens da empresa B abertos em {host}: {abertos}"
    assert b"Cliente empresab" not in respostas["lead"].content


@pytest.mark.parametrize("host", HOSTS)
def test_carrinho_nao_aceita_itens_da_outra_empresa(empresas, host):
    _, _, _, dados_b = empresas
    client = Client()

    client.post(
        reverse("cart:cart-add"),
        {
            "action": "post",
            "variation_id": dados_b["variacao"].pk,
            "product_quantity": 1,
        },
        HTTP_HOST=host,
    )

    sessao = client.session
    itens = [
        k
        for chave, carrinho in sessao.items()
        if chave.startswith("cart")
        for k in carrinho
    ]
    assert str(dados_b["variacao"].pk) not in itens


@pytest.mark.parametrize("host", HOSTS)
@pytest.mark.parametrize("papel", PAPEIS)
def test_apis_de_estoque_nao_expoem_variacoes_da_outra_empresa(empresas, papel, host):
    empresa_a, _, dados_a, dados_b = empresas
    client = _cliente(empresa_a, papel)

    saldo = client.get(
        reverse("estoque:saldo-variacao"),
        {
            "variacao_id": dados_b["variacao"].pk,
            "inventario_id": dados_a["inventario"].pk,
        },
        HTTP_HOST=host,
    )
    assert saldo.status_code != 200, "saldo de variação da empresa B exposto"

    busca = client.get(
        reverse("estoque:variacao-autocomplete"), {"term": ""}, HTTP_HOST=host
    )
    if busca.status_code == 200:
        ids = {r["id"] for r in busca.json()["results"]}
        assert dados_b["variacao"].pk not in ids, (
            "autocomplete lista variação da empresa B"
        )
