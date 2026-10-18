# Plano de implementação: saldo de estoque seguro sob concorrência

> Para quem for executar: siga as tarefas na ordem e escreva o teste antes do código (TDD). Cada tarefa termina num commit. Não pule o passo "rodar e ver falhar"; ele prova que o teste pega o problema.

- **Spec:** [2026-10-18-concorrencia-estoque-design.md](2026-10-18-concorrencia-estoque-design.md)
- **Issue:** #141
- **Objetivo:** tornar à prova de concorrência o processamento de movimentações e a aprovação de ordens; fazer a baixa sair do depósito padrão da empresa; impedir saldo negativo ou duplicado no banco.
- **Arquitetura:** trava pessimista (`select_for_update`) numa ordem fixa, concentrada em `estoque/locks.py`. `Estoque.processar()` e as transições de `OrdemCompraService` passam a rodar numa transação única com as linhas travadas. Constraints no Postgres servem de rede de segurança. As funções de checagem de saldo ficam em `estoque/saldos.py` e são usadas pela migration e pelo comando `verificar_saldos`.
- **Stack:** Django 5.1.7, PostgreSQL 16, pytest + pytest-django + factory-boy.

## Convenções

**Rodar testes.**

```bash
docker compose -f docker-compose.local.yml run --rm django pytest <caminho> -q
```

Sem Docker, use o Postgres local: `DATABASE_URL=postgres://app:app@localhost:5432/app USE_DOCKER=no pytest <caminho> -q`.

**Lint.** Rode só nos arquivos alterados. O repositório tem cerca de 2.959 erros pré-existentes, e `--fix` no projeto inteiro polui o diff.

```bash
ruff check <arquivos> && ruff format <arquivos>
```

**Branch.** `feat/concorrencia-estoque`, criada a partir da `main` atualizada.

**Commits.** Mensagens no padrão do repositório: `feat(estoque): ...`, `fix(vendas): ...`, `test(...)`.

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `estoque/exceptions.py` | alterar | `InventarioSaldoInsuficienteError` |
| `inventario/exceptions.py` | criar | `InventarioPadraoAusenteError` |
| `inventario/models.py` | alterar | campo `padrao`, manager `padrao_da_empresa`, `clean`, constraints de `InventarioSaldo` |
| `inventario/migrations/0007_inventario_padrao.py` | criar | campo e constraint de padrão único |
| `inventario/migrations/0008_marcar_inventario_padrao.py` | criar | migration de dados |
| `inventario/migrations/0009_inventariosaldo_constraints.py` | criar | checagem prévia, unicidade com nulos e saldo não negativo |
| `produto/models/produto_model.py` | alterar | `CheckConstraint` de estoque |
| `produto/migrations/0016_produto_estoque_nao_negativo.py` | criar | checagem prévia e constraint |
| `inventario/admin/gerente_admin.py` | alterar | campo `padrao` no admin; desmarcar o anterior |
| `estoque/saldos.py` | criar | consultas de negativos, duplicados e divergências; correção |
| `estoque/management/commands/verificar_saldos.py` | criar | comando |
| `estoque/locks.py` | criar | `travar_saldos()` em ordem fixa |
| `estoque/models/estoque_model.py` | alterar | novo `processar()` |
| `estoque/services.py` | alterar | depósito obrigatório; empresa na saída manual |
| `vendas/services/ordem_compra_service.py` | alterar | aprovação atômica, transições travadas, validação pelo depósito padrão |
| `inventario/tests/factories.py` | alterar | `padrao` na factory |
| `core/tests/concorrencia.py` | criar | helper `em_paralelo()` para testes com threads |
| testes novos em `inventario/tests/`, `estoque/tests/` e `vendas/tests/` | criar | ver cada tarefa |

---

## Tarefa 1: exceções novas

**Arquivos:** `estoque/exceptions.py`, criar `inventario/exceptions.py`, testes em `estoque/tests/test_exceptions.py`.

- [ ] **1.1 Escrever o teste**

```python
# estoque/tests/test_exceptions.py
from types import SimpleNamespace

from plataforma_de_servicos.estoque.exceptions import InventarioSaldoInsuficienteError
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError


def test_inventario_saldo_insuficiente_mostra_deposito_e_saldo():
    saldo = SimpleNamespace(inventario="Loja Centro", quantidade=2)
    erro = InventarioSaldoInsuficienteError(saldo, quantidade=5, item="Camiseta - P")
    assert "Loja Centro" in str(erro)
    assert "5" in str(erro)
    assert "2" in str(erro)


def test_inventario_padrao_ausente_cita_a_empresa():
    erro = InventarioPadraoAusenteError(SimpleNamespace(nome="Empresa A"))
    assert "Empresa A" in str(erro)
```

- [ ] **1.2 Rodar e ver falhar** (ImportError): `pytest plataforma_de_servicos/estoque/tests/test_exceptions.py -q`

- [ ] **1.3 Implementar**

```python
# estoque/exceptions.py (acrescentar)
class InventarioSaldoInsuficienteError(Exception):
    def __init__(self, saldo, quantidade, item):
        super().__init__(
            f"Saldo insuficiente de '{item}' no depósito {saldo.inventario}: "
            f"saldo {saldo.quantidade}, solicitado {quantidade}.",
        )
```

```python
# inventario/exceptions.py
class InventarioPadraoAusenteError(Exception):
    def __init__(self, empresa):
        super().__init__(
            f"A empresa {empresa.nome} não tem depósito padrão. "
            "Marque um inventário ativo como padrão no portal de gerentes.",
        )
```

- [ ] **1.4 Rodar e ver passar.**
- [ ] **1.5 Commit:** `feat(estoque): exceções de saldo de depósito e depósito padrão ausente`

---

## Tarefa 2: depósito padrão no modelo

**Arquivos:** `inventario/models.py`, `inventario/tests/factories.py`, migrations `0007` e `0008`, teste `inventario/tests/test_inventario_padrao.py`.

- [ ] **2.1 Escrever os testes**

```python
# inventario/tests/test_inventario_padrao.py
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError
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


def test_padrao_precisa_estar_ativo():
    inv = InventarioFactory.build(nome="Inativo", empresa=EmpresaFactory(), padrao=True, is_ativo=False)
    with pytest.raises(ValidationError):
        inv.clean()
```

- [ ] **2.2 Rodar e ver falhar.**

- [ ] **2.3 Implementar no modelo**

```python
# inventario/models.py
from django.core.exceptions import ValidationError
from django.db.models import Q

from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError


class InventarioManager(models.Manager):
    def padrao_da_empresa(self, empresa):
        inventario = self.filter(empresa=empresa, padrao=True, is_ativo=True).first()
        if inventario is None:
            raise InventarioPadraoAusenteError(empresa)
        return inventario


class Inventario(TimeStampedModel):
    # ... campos existentes ...
    padrao = models.BooleanField(
        default=False,
        verbose_name="Depósito padrão",
        help_text="As ordens aprovadas dão baixa neste depósito. Só um por empresa.",
    )

    objects = InventarioManager()

    class Meta:
        # ... existente ...
        constraints = [
            models.UniqueConstraint(fields=["empresa", "slug"], name="unique_empresa_inventario_slug"),
            models.UniqueConstraint(
                fields=["empresa"],
                condition=Q(padrao=True),
                name="unique_inventario_padrao_por_empresa",
            ),
        ]

    def clean(self):
        super().clean()
        if self.padrao and not self.is_ativo:
            raise ValidationError({"padrao": "O depósito padrão precisa estar ativo."})
```

Na factory, acrescente `padrao = False`.

- [ ] **2.4 Gerar a migration de schema:** `python manage.py makemigrations inventario --name inventario_padrao`. Confira que ela contém `AddField` e `AddConstraint`.

- [ ] **2.5 Escrever o teste da migration de dados**

A lógica fica numa função testável em `inventario/migrations_utils.py`, e a migration só a chama:

```python
# inventario/tests/test_inventario_padrao.py (acrescentar)
from plataforma_de_servicos.inventario.migrations_utils import marcar_padroes


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
```

- [ ] **2.6 Implementar a função e a migration de dados**

```python
# inventario/migrations_utils.py
def marcar_padroes(Inventario):
    """Marca um depósito padrão em cada empresa que ainda não tem.

    Recebe o model como parâmetro para funcionar com o model histórico da migration.
    """
    empresas_com_padrao = Inventario.objects.filter(padrao=True).values("empresa_id")
    candidatos = (
        Inventario.objects.filter(is_ativo=True, empresa__isnull=False)
        .exclude(empresa_id__in=empresas_com_padrao)
        .order_by("empresa_id", "-exibir_na_vitrine", "created")
    )
    vistas = set()
    for inventario in candidatos:
        if inventario.empresa_id in vistas:
            continue
        vistas.add(inventario.empresa_id)
        Inventario.objects.filter(pk=inventario.pk).update(padrao=True)
```

```python
# inventario/migrations/0008_marcar_inventario_padrao.py
from django.db import migrations

from plataforma_de_servicos.inventario.migrations_utils import marcar_padroes


def forwards(apps, schema_editor):
    marcar_padroes(apps.get_model("inventario", "Inventario"))


class Migration(migrations.Migration):
    dependencies = [("inventario", "0007_inventario_padrao")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
```

- [ ] **2.7 Rodar os testes e ver passar.** Rode também `python manage.py migrate` num banco com dados de seed (`seed_completo`) e confira uma empresa.
- [ ] **2.8 Commit:** `feat(inventario): depósito padrão por empresa`

---

## Tarefa 3: depósito padrão no admin

**Arquivos:** `inventario/admin/gerente_admin.py`, teste `inventario/tests/test_inventario_padrao_admin.py`.

- [ ] **3.1 Escrever os testes.** Use o padrão de request e cliente dos testes de admin existentes (`vendas/tests/test_ordem_compra_admin.py`).

```python
def test_marcar_novo_padrao_desmarca_o_anterior(client_gerente_empresa_a, empresa_a):
    antigo = InventarioFactory(nome="Antigo", empresa=empresa_a, padrao=True)
    novo = InventarioFactory(nome="Novo", empresa=empresa_a)
    url = reverse("gerentes:inventario_inventario_change", args=[novo.pk])
    resposta = client_gerente_empresa_a.post(url, {...campos do form..., "padrao": "on"}, HTTP_HOST="empresaa.localhost")
    assert resposta.status_code == 302
    antigo.refresh_from_db(); novo.refresh_from_db()
    assert novo.padrao and not antigo.padrao


def test_padrao_aparece_na_listagem(...):
    ...  # "padrao" em list_display
```

Se os fixtures `client_gerente_empresa_a`/`empresa_a` ainda não existirem, crie-os no `conftest.py` de `inventario/tests` seguindo `_cliente()` de `core/tests/test_isolamento_parametrico.py`.

- [ ] **3.2 Rodar e ver falhar.**

- [ ] **3.3 Implementar**
  - `list_display` passa a incluir `"padrao"`; `list_filter` também.
  - Em `fieldsets`, o campo `"padrao"` entra em "Configurações de Exibição", com a descrição "As ordens aprovadas dão baixa no depósito padrão".
  - `save_model`:

```python
def save_model(self, request, obj, form, change):
    with transaction.atomic():
        if obj.padrao:
            Inventario.objects.filter(empresa=obj.empresa, padrao=True).exclude(pk=obj.pk).update(padrao=False)
        super().save_model(request, obj, form, change)
```

- [ ] **3.4 Rodar e ver passar.**
- [ ] **3.5 Commit:** `feat(inventario): depósito padrão editável no portal de gerentes`

---

## Tarefa 4: consultas de saldo e comando `verificar_saldos`

**Arquivos:** criar `estoque/saldos.py`, `estoque/management/commands/verificar_saldos.py` e `estoque/tests/test_verificar_saldos.py`.

As funções recebem as classes de model como parâmetro para servir também à migration (Tarefa 5).

- [ ] **4.1 Escrever os testes**

```python
# estoque/tests/test_verificar_saldos.py
import pytest
from django.core.management import call_command

from plataforma_de_servicos.estoque import saldos
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory, InventarioSaldoFactory
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory, VariacaoProdutoFactory

pytestmark = pytest.mark.django_db


def test_lista_saldo_negativo_de_deposito():
    s = InventarioSaldoFactory(quantidade=-3)
    assert list(saldos.saldos_negativos(InventarioSaldo)) == [s]


def test_lista_divergencia_entre_variacao_e_depositos():
    v = VariacaoProdutoFactory(estoque=10)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    divergentes = list(saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo))
    assert [(d.pk, d.estoque, d.total_depositos) for d in divergentes] == [(v.pk, 10, 7)]


def test_produto_sem_nenhum_deposito_e_listado_a_parte_e_nao_e_corrigido():
    p = ProdutoFactory(estoque=5)
    assert p in saldos.produtos_sem_deposito(Produto, InventarioSaldo)
    saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo)
    p.refresh_from_db()
    assert p.estoque == 5


def test_corrigir_recalcula_produto_e_variacao_a_partir_dos_depositos():
    v = VariacaoProdutoFactory(estoque=10)
    v.produto.estoque = 10; v.produto.save()
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo)
    v.refresh_from_db(); v.produto.refresh_from_db()
    assert v.estoque == 7 and v.produto.estoque == 7


def test_corrigir_nao_mexe_em_saldo_negativo_de_deposito():
    s = InventarioSaldoFactory(quantidade=-3)
    saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo)
    s.refresh_from_db()
    assert s.quantidade == -3


def test_comando_sai_com_codigo_1_quando_ha_problema(capsys):
    InventarioSaldoFactory(quantidade=-1)
    with pytest.raises(SystemExit) as saida:
        call_command("verificar_saldos")
    assert saida.value.code == 1
    assert "negativo" in capsys.readouterr().out.lower()


def test_comando_sem_problemas_termina_ok(capsys):
    call_command("verificar_saldos")
    assert "nenhum problema" in capsys.readouterr().out.lower()
```

Os duplicados (`saldos_duplicados`) só conseguem ser criados antes da constraint da Tarefa 5. Teste a função com um `InventarioSaldo` inserido por `bulk_create` num teste marcado para rodar contra o estado anterior à migration 0009, usando o padrão `migrator` do `django-test-migrations` se estiver disponível. Se não estiver, teste a função só pela consulta (`values(...).annotate(n=Count("id")).filter(n__gt=1)`) com objetos em memória mockados, e registre a limitação no PR.

- [ ] **4.2 Rodar e ver falhar.**

- [ ] **4.3 Implementar `estoque/saldos.py`**

```python
from django.db import transaction
from django.db.models import Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce


def _soma_depositos(InventarioSaldo, **filtro_ref):
    return Coalesce(
        Subquery(
            InventarioSaldo.objects.filter(**filtro_ref)
            .values(*filtro_ref.keys())
            .annotate(t=Sum("quantidade"))
            .values("t")[:1],
            output_field=IntegerField(),
        ),
        Value(0),
    )


def saldos_negativos(InventarioSaldo):
    return InventarioSaldo.objects.filter(quantidade__lt=0)


def saldos_duplicados(InventarioSaldo):
    return (
        InventarioSaldo.objects.values("inventario_id", "produto_id", "variacao_id")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )


def variacoes_divergentes(VariacaoProduto, InventarioSaldo):
    return (
        VariacaoProduto.objects.filter(Q(inventariosaldo__isnull=False))
        .distinct()
        .annotate(total_depositos=_soma_depositos(InventarioSaldo, variacao=OuterRef("pk")))
        .exclude(estoque=F("total_depositos"))
    )


def produtos_divergentes(Produto, InventarioSaldo):
    return (
        Produto.objects.filter(inventariosaldo__isnull=False)
        .distinct()
        .annotate(total_depositos=_soma_depositos(InventarioSaldo, produto=OuterRef("pk")))
        .exclude(estoque=F("total_depositos"))
    )


def produtos_sem_deposito(Produto, InventarioSaldo):
    return Produto.objects.filter(inventariosaldo__isnull=True, estoque__gt=0)


@transaction.atomic
def corrigir(Produto, VariacaoProduto, InventarioSaldo):
    """Recalcula produto e variação pela soma dos depósitos e junta duplicados.

    Não altera saldo negativo de depósito nem itens sem nenhum depósito.
    """
    for dup in saldos_duplicados(InventarioSaldo):
        linhas = list(
            InventarioSaldo.objects.select_for_update()
            .filter(inventario_id=dup["inventario_id"], produto_id=dup["produto_id"], variacao_id=dup["variacao_id"])
            .order_by("pk")
        )
        manter, sobras = linhas[0], linhas[1:]
        manter.quantidade = sum(l.quantidade for l in linhas)
        manter.save(update_fields=["quantidade"])
        InventarioSaldo.objects.filter(pk__in=[s.pk for s in sobras]).delete()
    for v in variacoes_divergentes(VariacaoProduto, InventarioSaldo):
        VariacaoProduto.objects.filter(pk=v.pk).update(estoque=max(v.total_depositos, 0))
    for p in produtos_divergentes(Produto, InventarioSaldo):
        Produto.objects.filter(pk=p.pk).update(estoque=max(p.total_depositos, 0))
```

O nome reverso `inventariosaldo` precisa ser conferido no shell (`Produto._meta.related_objects`). Se `InventarioSaldo` tiver `related_name`, use-o.

- [ ] **4.4 Implementar o comando**

```python
# estoque/management/commands/verificar_saldos.py
import sys

from django.core.management.base import BaseCommand

from plataforma_de_servicos.estoque import saldos
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto


class Command(BaseCommand):
    help = "Lista saldos negativos, duplicados e divergentes; com --corrigir, recalcula pelos depósitos."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", help="slug da empresa")
        parser.add_argument("--corrigir", action="store_true")

    def handle(self, *args, empresa=None, corrigir=False, **opts):
        # filtrar os querysets por empresa quando --empresa for informado
        # (InventarioSaldo: inventario__empresa__slug; Produto/VariacaoProduto: empresa__slug / produto__empresa__slug)
        if corrigir:
            saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo)
        problemas = self._relatorio()
        if problemas:
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("Nenhum problema de saldo encontrado."))

    def _relatorio(self):
        # imprime, por seção, até 50 linhas de: saldos negativos, duplicados,
        # variações divergentes, produtos divergentes, produtos sem depósito
        # e devolve o total de problemas (produtos sem depósito só alertam, não contam)
        ...
```

- [ ] **4.5 Rodar e ver passar.** Rode também `python manage.py verificar_saldos` no banco de seed e anote a saída no PR.
- [ ] **4.6 Commit:** `feat(estoque): comando verificar_saldos`

---

## Tarefa 5: constraints no banco

**Arquivos:** `inventario/models.py`, `produto/models/produto_model.py`, migrations `inventario/0009` e `produto/0016`, teste `estoque/tests/test_constraints_saldo.py`.

- [ ] **5.1 Escrever os testes**

```python
# estoque/tests/test_constraints_saldo.py
import pytest
from django.db import IntegrityError, transaction

from plataforma_de_servicos.estoque.saldos_migracao import checar_antes_das_constraints

pytestmark = pytest.mark.django_db


def test_saldo_de_deposito_nao_pode_ser_negativo():
    s = InventarioSaldoFactory(quantidade=1)
    s.quantidade = -1
    with pytest.raises(IntegrityError), transaction.atomic():
        s.save()


def test_estoque_de_produto_nao_pode_ser_negativo():
    p = ProdutoFactory(estoque=0)
    p.estoque = -1
    with pytest.raises(IntegrityError), transaction.atomic():
        p.save()


def test_estoque_de_produto_pode_ser_nulo():
    ProdutoFactory(estoque=None)


def test_saldo_duplicado_sem_variacao_e_recusado():
    inv, prod = InventarioFactory(), ProdutoFactory()
    InventarioSaldoFactory(inventario=inv, produto=prod, variacao=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        InventarioSaldoFactory(inventario=inv, produto=prod, variacao=None)


def test_checagem_previa_lista_os_negativos():
    class FakeQS(list):
        def exists(self): return bool(self)
    with pytest.raises(RuntimeError, match="verificar_saldos"):
        checar_antes_das_constraints(negativos=FakeQS(["saldo 1"]), duplicados=FakeQS())
```

- [ ] **5.2 Rodar e ver falhar.**

- [ ] **5.3 Implementar**

```python
# estoque/saldos_migracao.py
def checar_antes_das_constraints(negativos, duplicados, limite=20):
    """Interrompe a migration listando os registros que violariam as constraints."""
    linhas = [f"saldo negativo: {r}" for r in list(negativos[:limite])]
    linhas += [f"saldo duplicado: {r}" for r in list(duplicados[:limite])]
    if linhas:
        raise RuntimeError(
            "Existem saldos que impedem criar as constraints de estoque:\n"
            + "\n".join(linhas)
            + "\nRode `python manage.py verificar_saldos` para ver tudo e "
            "`verificar_saldos --corrigir` ou movimentações de entrada para corrigir.",
        )
```

Nos models:
- **Produto:** `Meta.constraints = [models.CheckConstraint(condition=Q(estoque__gte=0) | Q(estoque__isnull=True), name="produto_estoque_nao_negativo")]`.
- **InventarioSaldo:** remova `unique_together` e acrescente:

```python
constraints = [
    models.UniqueConstraint(
        fields=["inventario", "produto", "variacao"],
        name="unique_saldo_por_inventario_produto_variacao",
        nulls_distinct=False,
    ),
    models.CheckConstraint(condition=Q(quantidade__gte=0), name="inventariosaldo_quantidade_nao_negativa"),
]
```

Gere as migrations com `makemigrations` e insira o `RunPython` como **primeira** operação de cada uma:

```python
def checar(apps, schema_editor):
    from plataforma_de_servicos.estoque.saldos import saldos_duplicados, saldos_negativos
    from plataforma_de_servicos.estoque.saldos_migracao import checar_antes_das_constraints
    S = apps.get_model("inventario", "InventarioSaldo")
    checar_antes_das_constraints(saldos_negativos(S), saldos_duplicados(S))
```

Para `produto/0016`, use `Produto.objects.filter(estoque__lt=0)` como negativos e uma lista vazia como duplicados.

- [ ] **5.4 Rodar os testes novos e a suíte de estoque, inventário e vendas.** Algum teste existente pode estar criando saldo negativo de propósito; nesse caso, ajuste o teste para esperar o erro.
- [ ] **5.5 Testar a parada da migration:** num banco local, rode `migrate inventario 0008`, faça `UPDATE inventario_inventariosaldo SET quantidade = -1 WHERE id = <id>` e depois `migrate`. Ela deve falhar com a lista. Volte o valor e confira que passa.
- [ ] **5.6 Commit:** `feat(estoque): constraints de saldo não negativo e unicidade com nulos`

---

## Tarefa 6: helper de testes de concorrência

**Arquivo:** criar `core/tests/concorrencia.py`.

```python
import threading

from django.db import connection


def em_paralelo(*funcoes, timeout=30):
    """Executa as funções em threads, liberadas juntas por uma barreira.

    Devolve uma lista de ("ok", resultado) ou ("erro", exceção), na ordem das funções.
    Cada thread usa e fecha a própria conexão.
    """
    barreira = threading.Barrier(len(funcoes))
    resultados = [None] * len(funcoes)

    def rodar(i, f):
        try:
            barreira.wait()
            resultados[i] = ("ok", f())
        except Exception as exc:  # noqa: BLE001
            resultados[i] = ("erro", exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=rodar, args=(i, f)) for i, f in enumerate(funcoes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout)
        assert not t.is_alive(), "thread presa: possível deadlock"
    return resultados


def atrasar_save(monkeypatch, model, segundos=0.2):
    """Faz model.save dormir antes de gravar, para abrir a janela de corrida."""
    import time

    original = model.save

    def save(self, *args, **kwargs):
        time.sleep(segundos)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(model, "save", save)
```

- [ ] **6.1 Commit:** `test(core): helper para testes de concorrência com threads`

O helper é exercitado pelos testes das Tarefas 8 e 12.

---

## Tarefa 7: travas em ordem fixa

**Arquivos:** criar `estoque/locks.py` e `estoque/tests/test_locks.py`.

- [ ] **7.1 Escrever os testes**

```python
# estoque/tests/test_locks.py
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from plataforma_de_servicos.estoque.locks import travar_saldos

pytestmark = pytest.mark.django_db


def test_itens_da_mesma_variacao_compartilham_a_instancia(entrada_com_dois_itens_da_mesma_variacao):
    estoque, itens = entrada_com_dois_itens_da_mesma_variacao
    travas = travar_saldos(estoque, itens)
    assert len(travas.variacoes) == 1
    assert len(travas.produtos) == 1


def test_trava_na_ordem_saldos_variacoes_produtos(entrada_com_dois_produtos):
    estoque, itens = entrada_com_dois_produtos
    with CaptureQueriesContext(connection) as ctx:
        travar_saldos(estoque, itens)
    travas = [q["sql"] for q in ctx.captured_queries if "FOR UPDATE" in q["sql"]]
    tabelas = [next(t for t in ("inventariosaldo", "variacaoproduto", "produto_produto") if t in sql) for sql in travas]
    assert tabelas == sorted(tabelas, key=["inventariosaldo", "variacaoproduto", "produto_produto"].index)


def test_cria_saldo_de_deposito_que_nao_existe(entrada_para_deposito_vazio):
    estoque, itens = entrada_para_deposito_vazio
    travas = travar_saldos(estoque, itens)
    (saldo,) = travas.saldos.values()
    assert saldo.pk and saldo.quantidade == 0
```

As fixtures criam um `Estoque` com `EstoqueItens` usando as factories existentes; ponha-as em `estoque/tests/conftest.py`.

- [ ] **7.2 Rodar e ver falhar.**

- [ ] **7.3 Implementar**

```python
# estoque/locks.py
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto


@dataclass
class Travas:
    saldos: dict = field(default_factory=dict)     # (inventario_id, produto_id, variacao_id) -> InventarioSaldo
    variacoes: dict = field(default_factory=dict)  # pk -> VariacaoProduto
    produtos: dict = field(default_factory=dict)   # pk -> Produto


def inventarios_do_movimento(estoque):
    if estoque.movimento == Movimento.ENTRADA.value:
        return [estoque.inventario_destino]
    if estoque.movimento == Movimento.SAIDA.value:
        return [estoque.inventario_origem]
    return [estoque.inventario_origem, estoque.inventario_destino]


def _travar_ou_criar_saldo(inventario_id, produto_id, variacao_id):
    filtro = {"inventario_id": inventario_id, "produto_id": produto_id, "variacao_id": variacao_id}
    try:
        return InventarioSaldo.objects.select_for_update().get(**filtro)
    except InventarioSaldo.DoesNotExist:
        try:
            with transaction.atomic():
                return InventarioSaldo.objects.create(quantidade=0, **filtro)
        except IntegrityError:
            return InventarioSaldo.objects.select_for_update().get(**filtro)


def travar_saldos(estoque, itens):
    """Trava, em ordem fixa, todas as linhas de saldo tocadas pela movimentação.

    Ordem: InventarioSaldo (por inventario, produto, variacao), VariacaoProduto (pk), Produto (pk).
    Precisa rodar dentro de transaction.atomic(), depois de travar a própria movimentação.
    """
    travas = Travas()
    inventarios = [i for i in inventarios_do_movimento(estoque) if i is not None]
    chaves = sorted(
        {(inv.pk, it.produto_id, it.variacao_id) for it in itens for inv in inventarios},
        key=lambda c: (c[0], c[1], c[2] or 0),
    )
    for chave in chaves:
        travas.saldos[chave] = _travar_ou_criar_saldo(*chave)

    ids_var = sorted({it.variacao_id for it in itens if it.variacao_id})
    travas.variacoes = {v.pk: v for v in VariacaoProduto.objects.select_for_update().filter(pk__in=ids_var).order_by("pk")}

    ids_prod = sorted({it.produto_id for it in itens})
    travas.produtos = {p.pk: p for p in Produto.objects.select_for_update().filter(pk__in=ids_prod).order_by("pk")}
    return travas
```

Atenção: `select_for_update()` com `filter(pk__in=...).order_by("pk")` trava as linhas na ordem do `ORDER BY` no Postgres. Isso é o que garante a ordem dentro de cada grupo.

- [ ] **7.4 Rodar e ver passar.**
- [ ] **7.5 Commit:** `feat(estoque): travas de saldo em ordem fixa`

---

## Tarefa 8: `Estoque.processar()` com travas

**Arquivos:** `estoque/models/estoque_model.py`, testes `estoque/tests/test_processar_travado.py` e `estoque/tests/test_processar_concorrencia.py`.

- [ ] **8.1 Escrever os testes de comportamento (sequenciais)**

```python
# estoque/tests/test_processar_travado.py
pytestmark = pytest.mark.django_db


def test_processar_duas_vezes_aplica_uma(entrada_de_5_na_variacao):
    estoque, variacao = entrada_de_5_na_variacao
    estoque.processar()
    Estoque.objects.get(pk=estoque.pk).processar()   # outra instância, como faria outro request
    variacao.refresh_from_db()
    assert variacao.estoque == 5


def test_saida_maior_que_o_saldo_do_deposito_falha_mesmo_com_total_suficiente(variacao_com_10_em_dois_depositos):
    # 10 no total: 2 no depósito A e 8 no B; saída de 5 do A
    with pytest.raises(InventarioSaldoInsuficienteError):
        saida_de(variacao, 5, deposito_a).processar()
    assert_nada_mudou(...)


def test_transferencia_sem_saldo_na_origem_falha(...): ...


def test_saida_nao_sobrescreve_campos_editados_do_produto(produto_com_saldo):
    saida = saida_de(produto_com_saldo, 1, deposito)
    Produto.objects.filter(pk=produto_com_saldo.pk).update(preco=Decimal("99.90"))  # edição "concorrente"
    saida.processar()
    produto_com_saldo.refresh_from_db()
    assert produto_com_saldo.preco == Decimal("99.90")


def test_saldo_anterior_e_saldo_do_item_refletem_valores_travados(...): ...


def test_entrada_saida_e_transferencia_mantem_os_tres_saldos_iguais(...):
    # roda E, S e T e confere que variação, produto e soma dos depósitos batem
    ...
```

- [ ] **8.2 Escrever os testes de concorrência**

```python
# estoque/tests/test_processar_concorrencia.py
import pytest

from plataforma_de_servicos.core.tests.concorrencia import atrasar_save, em_paralelo

pytestmark = pytest.mark.django_db(transaction=True)


def test_mesma_movimentacao_em_paralelo_aplica_uma_vez(monkeypatch, entrada_de_5_na_variacao):
    estoque, variacao = entrada_de_5_na_variacao
    atrasar_save(monkeypatch, VariacaoProduto)
    em_paralelo(
        lambda: Estoque.objects.get(pk=estoque.pk).processar(),
        lambda: Estoque.objects.get(pk=estoque.pk).processar(),
    )
    variacao.refresh_from_db()
    assert variacao.estoque == 5


def test_duas_saidas_simultaneas_terminam_com_os_tres_saldos_corretos(monkeypatch, variacao_com_10_no_deposito):
    s1, s2 = saida_de(variacao, 1, deposito), saida_de(variacao, 1, deposito)
    atrasar_save(monkeypatch, VariacaoProduto)
    resultados = em_paralelo(s1.processar, s2.processar)
    assert all(r[0] == "ok" for r in resultados)
    assert_saldos(variacao, deposito, esperado=8)   # variação, produto e InventarioSaldo


def test_saidas_simultaneas_acima_do_saldo_uma_falha(monkeypatch, variacao_com_10_no_deposito):
    s1, s2 = saida_de(variacao, 6, deposito), saida_de(variacao, 6, deposito)
    resultados = em_paralelo(s1.processar, s2.processar)
    assert sorted(r[0] for r in resultados) == ["erro", "ok"]
    assert_saldos(variacao, deposito, esperado=4)


def test_movimentacoes_cruzadas_nao_entram_em_deadlock(dois_produtos_com_saldo):
    # m1 tem itens [A, B]; m2 tem itens [B, A]
    resultados = em_paralelo(m1.processar, m2.processar)
    assert all(r[0] == "ok" for r in resultados)
```

`saida_de`, `assert_saldos` e as fixtures ficam em `estoque/tests/conftest.py`.

- [ ] **8.3 Rodar e ver falhar contra o código atual.** O mais importante é o teste de duas saídas, que deve terminar com variação em 9 e depósito em 8. Anote as falhas no PR como prova.

- [ ] **8.4 Implementar**

```python
# estoque/models/estoque_model.py
from django.db import connection, transaction

from plataforma_de_servicos.estoque.exceptions import (
    InventarioSaldoInsuficienteError, ProdutoSaldoInsuficienteError, VariacaoSaldoInsuficienteError,
)


class Estoque(models.Model):
    ...

    @transaction.atomic
    def processar(self):
        """Aplica a movimentação aos saldos uma única vez, com as linhas travadas."""
        from plataforma_de_servicos.estoque.locks import travar_saldos

        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '5s'")
        estoque = type(self).objects.select_for_update().get(pk=self.pk)
        if estoque.processado:
            self.processado = True
            return
        itens = list(estoque.estoque_itens.select_related("produto", "variacao"))
        travas = travar_saldos(estoque, itens)
        for item in itens:
            estoque._aplicar_item(item, travas)
        for v in travas.variacoes.values():
            v.save(update_fields=["estoque"])
        for p in travas.produtos.values():
            p.save(update_fields=["estoque"])
        for s in travas.saldos.values():
            s.save(update_fields=["quantidade", "atualizado_em"])
        estoque.processado = True
        estoque.save(update_fields=["processado"])
        self.processado = True

    def _aplicar_item(self, item, travas):
        produto = travas.produtos[item.produto_id]
        variacao = travas.variacoes.get(item.variacao_id)
        q = item.quantidade
        origem = self.inventario_origem_id
        destino = self.inventario_destino_id
        chave = lambda inv: (inv, item.produto_id, item.variacao_id)  # noqa: E731

        if self.movimento == Movimento.ENTRADA.value:
            delta_total, deltas = q, {chave(destino): q}
            item.inventario_id = destino
        elif self.movimento == Movimento.SAIDA.value:
            delta_total, deltas = -q, {chave(origem): -q}
            item.inventario_id = origem
        else:  # transferência
            delta_total, deltas = 0, {chave(origem): -q, chave(destino): q}
            item.inventario_id = origem

        referencia = variacao or produto
        item.saldo_anterior = referencia.estoque or 0

        if variacao is not None and variacao.estoque + delta_total < 0:
            raise VariacaoSaldoInsuficienteError(variacao, q)
        if (produto.estoque or 0) + delta_total < 0:
            raise ProdutoSaldoInsuficienteError(produto.produto, q)
        for k, d in deltas.items():
            saldo = travas.saldos[k]
            if saldo.quantidade + d < 0:
                raise InventarioSaldoInsuficienteError(saldo, q, item=str(variacao or produto.produto))

        if variacao is not None:
            variacao.estoque += delta_total
        produto.estoque = (produto.estoque or 0) + delta_total
        for k, d in deltas.items():
            travas.saldos[k].quantidade += d

        item.saldo = referencia.estoque
        item.save(update_fields=["saldo_anterior", "saldo", "inventario"])
```

Remova `atualizar_estoque`, `atualizar_inventario_saldo` e `_atualizar_inventario` do `Estoque`. Remova também `atualizar_saldo`, `_atualizar_saldo_produto` e `_atualizar_saldo_variacao` do `EstoqueItens`, depois de confirmar com `grep -rn` que só `Estoque` os chama. Se algum teste os chamar diretamente, migre-o para `processar()`.

- [ ] **8.5 Rodar** `estoque/tests` e `inventario/tests` inteiros. O teste de signal de `disponivel` (`inventario/tests/test_signals.py`) precisa continuar passando.
- [ ] **8.6 Commit:** `fix(estoque): processar movimentação uma vez e com saldos travados`

---

## Tarefa 9: `EstoqueService` exige o depósito

**Arquivos:** `estoque/services.py` e `estoque/tests/test_estoque_service.py`.

- [ ] **9.1 Ajustar e escrever os testes**
  - `test_criar_saida_sem_inventario` passa a esperar `ValueError("inventario_origem é obrigatório")` e não usa mais o mock de `Inventario.objects.first`.
  - Novo teste: `criar_saida_manual` grava `empresa` igual a `inventario_origem.empresa`.
  - Novo teste: `criar_saida_por_ordem_compra` com depósito de outra empresa levanta `ValueError`.
  - Os demais testes passam a criar o depósito com saldo usando `InventarioSaldoFactory`. Hoje alguns dependem só de `produto.estoque`.

- [ ] **9.2 Rodar e ver falhar.**

- [ ] **9.3 Implementar**
  - Retire os dois `if not inventario_origem: inventario_origem = Inventario.objects.first()`.
  - No início de cada função: `if inventario_origem is None: raise ValueError("inventario_origem é obrigatório")`.
  - Em `criar_saida_por_ordem_compra`: `if inventario_origem.empresa_id != ordem_compra.empresa_id: raise ValueError("depósito de outra empresa")`.
  - Em `criar_saida_manual`: `Estoque.objects.create(empresa=inventario_origem.empresa, ...)`.

- [ ] **9.4 Rodar e ver passar.**
- [ ] **9.5 Commit:** `fix(estoque): saídas exigem depósito da própria empresa`

---

## Tarefa 10: aprovação atômica pelo depósito padrão

**Arquivos:** `vendas/services/ordem_compra_service.py`, `vendas/tests/conftest.py` (ou os fixtures existentes) e `vendas/tests/test_aprovacao_deposito_padrao.py`.

- [ ] **10.1 Ajustar os fixtures existentes.** `ordem_compra_pendente` e as ordens usadas em `test_ordem_compra.py` e `test_ordem_compra_admin.py` passam a ter um depósito padrão na empresa da ordem, com `InventarioSaldo` suficiente para cada item. Sem isso, os testes de aprovação que já passam vão falhar pela regra nova.

- [ ] **10.2 Escrever os testes novos**

```python
# vendas/tests/test_aprovacao_deposito_padrao.py
pytestmark = pytest.mark.django_db


def test_baixa_sai_do_deposito_padrao_da_empresa_da_ordem(ordem_empresa_a, deposito_padrao_a, deposito_empresa_b_mais_recente):
    OrdemCompraService.aprovar(ordem_empresa_a, usuario)
    saida = Estoque.objects.get(ordem_compra=ordem_empresa_a)
    assert saida.inventario_origem == deposito_padrao_a


def test_empresa_sem_padrao_nao_aprova_e_nao_grava_nada(ordem_sem_deposito_padrao):
    with pytest.raises(OrdemCompraServiceError, match="depósito padrão"):
        OrdemCompraService.aprovar(ordem_sem_deposito_padrao, usuario)
    ordem_sem_deposito_padrao.refresh_from_db()
    assert ordem_sem_deposito_padrao.status == StatusOrdemCompra.PENDENTE_APROVACAO
    assert not Estoque.objects.filter(ordem_compra=ordem_sem_deposito_padrao).exists()
    assert not Comissao.objects.filter(ordem=ordem_sem_deposito_padrao).exists()


def test_saldo_insuficiente_no_padrao_vira_erro_de_estoque_e_desfaz_tudo(ordem_com_saldo_so_em_outro_deposito):
    with pytest.raises(EstoqueInsuficienteError):
        OrdemCompraService.aprovar(ordem_com_saldo_so_em_outro_deposito, usuario)
    # status, saída, comissão e saldos intactos


def test_validar_estoque_usa_o_saldo_do_deposito_padrao(ordem_com_saldo_so_em_outro_deposito):
    resultado = OrdemCompraService.validar_estoque(ordem_com_saldo_so_em_outro_deposito)
    assert not resultado.is_valid


def test_admin_mostra_mensagem_de_erro_em_vez_de_500(...):
    # action_aprovar com saldo insuficiente → messages.ERROR, sem exceção
    ...
```

- [ ] **10.3 Rodar e ver falhar.**

- [ ] **10.4 Implementar**

```python
# vendas/services/ordem_compra_service.py
from plataforma_de_servicos.estoque.exceptions import (
    InventarioSaldoInsuficienteError, ProdutoSaldoInsuficienteError, VariacaoSaldoInsuficienteError,
)
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError
from plataforma_de_servicos.inventario.models import Inventario

ERROS_DE_SALDO = (InventarioSaldoInsuficienteError, ProdutoSaldoInsuficienteError, VariacaoSaldoInsuficienteError)


class OrdemCompraService:
    @staticmethod
    def _travar(ordem):
        return OrdemCompra.objects.select_for_update().get(pk=ordem.pk)

    @staticmethod
    def _deposito_padrao(empresa):
        try:
            return Inventario.objects.padrao_da_empresa(empresa)
        except InventarioPadraoAusenteError as exc:
            raise OrdemCompraServiceError(str(exc)) from exc

    @staticmethod
    @transaction.atomic
    def aprovar(ordem, usuario):
        travada = OrdemCompraService._travar(ordem)
        if not travada.pode_aprovar:
            raise OrdemCompraServiceError(
                f"Ordem {travada.numero} não pode ser aprovada. Status atual: {travada.get_status_display()}",
            )
        deposito = OrdemCompraService._deposito_padrao(travada.empresa)
        itens_pedido = [
            {"produto": i.produto, "variacao": i.variacao, "quantidade": i.quantidade}
            for i in travada.itens.select_related("produto", "variacao")
            if i.produto
        ]
        if itens_pedido:
            try:
                EstoqueService.criar_saida_por_ordem_compra(
                    ordem_compra=travada, itens_pedido=itens_pedido,
                    funcionario=usuario, inventario_origem=deposito,
                )
            except ERROS_DE_SALDO as exc:
                raise EstoqueInsuficienteError(
                    f"Não é possível aprovar a ordem {travada.numero}. {exc}",
                ) from exc
        travada.status = StatusOrdemCompra.APROVADA
        travada.aprovado_por = usuario
        travada.data_aprovacao = timezone.now()
        travada.save(update_fields=["status", "aprovado_por", "data_aprovacao", "atualizado_em"])
        if travada.corretor:
            from plataforma_de_servicos.vendas.services.commission_service import CommissionService
            CommissionService(travada.empresa).criar_comissao(travada)
        ordem.refresh_from_db()
        return ordem
```

Ajustes que acompanham o código acima:
- Confira o nome real do campo de data de atualização em `OrdemCompra` e corrija o `update_fields`.
- O parâmetro `skip_stock_validation` sai. Hoje nenhum chamador o usa (conferido com `grep`), e com a checagem dentro de `processar()` ele não teria efeito.
- `validar_estoque(ordem)` passa a usar `obter_estoque_disponivel_item(produto, variacao, deposito.pk)`. Se a empresa não tiver depósito padrão, devolve resultado inválido com a mensagem do erro, sem levantar.
- Em `criar_ordem_manual`, quando `inventario_origem_id` é `None`, use o id do depósito padrão da empresa. Se não houver padrão, levante `OrdemCompraServiceError` só quando `validate_stock=True`.

- [ ] **10.5 Rodar** `vendas/tests` e `estoque/tests` inteiros.
- [ ] **10.6 Commit:** `fix(vendas): aprovação atômica com baixa do depósito padrão da empresa`

---

## Tarefa 11: demais transições com a ordem travada

**Arquivos:** `vendas/services/ordem_compra_service.py` e `vendas/tests/test_ordem_compra_service.py`.

- [ ] **11.1 Escrever um teste por transição.** Carregue a ordem em duas instâncias. A primeira faz a transição; a segunda, ainda com o status antigo em memória, tenta a mesma transição e precisa receber `OrdemCompraServiceError`, porque a checagem é feita no registro travado e não na instância.

```python
@pytest.mark.parametrize("acao,status_inicial", [
    ("rejeitar", StatusOrdemCompra.PENDENTE_APROVACAO),
    ("faturar", StatusOrdemCompra.APROVADA),
    ("cancelar", StatusOrdemCompra.APROVADA),
    ("concluir", StatusOrdemCompra.FATURADA),
])
def test_transicao_checa_status_no_registro_travado(acao, status_inicial, ...):
    a = OrdemCompraFactory(status=status_inicial, ...)
    b = OrdemCompra.objects.get(pk=a.pk)
    executar(acao, a)
    with pytest.raises(OrdemCompraServiceError):
        executar(acao, b)
```

- [ ] **11.2 Rodar e ver falhar.**
- [ ] **11.3 Implementar.** Em `rejeitar`, `faturar`, `cancelar` e `concluir`: decorar com `@transaction.atomic`, trocar `ordem` por `travada = OrdemCompraService._travar(ordem)` para checar `pode_*` e salvar, e terminar com `ordem.refresh_from_db(); return ordem`.
- [ ] **11.4 Rodar e ver passar.**
- [ ] **11.5 Commit:** `fix(vendas): transições da ordem checam status com a linha travada`

---

## Tarefa 12: concorrência na aprovação

**Arquivo:** `vendas/tests/test_aprovacao_concorrencia.py`.

```python
pytestmark = pytest.mark.django_db(transaction=True)


def test_duas_aprovacoes_simultaneas_geram_uma_saida_e_uma_comissao(monkeypatch, ordem_com_corretor_e_saldo):
    ordem = ordem_com_corretor_e_saldo
    atrasar_save(monkeypatch, VariacaoProduto)
    resultados = em_paralelo(
        lambda: OrdemCompraService.aprovar(OrdemCompra.objects.get(pk=ordem.pk), usuario),
        lambda: OrdemCompraService.aprovar(OrdemCompra.objects.get(pk=ordem.pk), usuario),
    )
    assert sorted(r[0] for r in resultados) == ["erro", "ok"]
    assert Estoque.objects.filter(ordem_compra=ordem).count() == 1
    assert Comissao.objects.filter(ordem=ordem).count() == 1


def test_duas_ordens_disputando_o_ultimo_item_so_uma_aprova(monkeypatch, duas_ordens_de_1_com_saldo_1):
    resultados = em_paralelo(...)
    assert sorted(r[0] for r in resultados) == ["erro", "ok"]
    # saldo final 0 nos três lugares
```

- [ ] **12.1 Rodar contra a branch antes da Tarefa 10** (por exemplo com `git stash`) para ver falhar, e depois na versão final para ver passar.
- [ ] **12.2 Commit:** `test(vendas): aprovação concorrente da mesma ordem e do último item`

---

## Tarefa 13: verificação final e PR

- [ ] **13.1** Rodar a suíte inteira: `pytest plataforma_de_servicos -q`. Todos os testes passam, incluindo os 692 que existiam antes.
- [ ] **13.2** Rodar `ruff check` e `ruff format` nos arquivos alterados.
- [ ] **13.3** Rodar `python manage.py makemigrations --check --dry-run` e confirmar que não sobrou migration pendente.
- [ ] **13.4** Num banco com o seed: `migrate`, depois `verificar_saldos`, depois aprovar uma ordem pelo portal e conferir de qual depósito a baixa saiu.
- [ ] **13.5** Copiar a spec e este plano para `docs/superpowers/specs/` no repositório, no mesmo PR.
- [ ] **13.6** Abrir o PR "Saldo de estoque seguro sob concorrência" com `Closes #141`, o antes/depois, as falhas dos testes de concorrência contra o código antigo (Tarefas 8.3 e 12.1) e as instruções de deploy:
  1. rodar `verificar_saldos` em produção;
  2. corrigir o que aparecer;
  3. aplicar as migrations;
  4. conferir o depósito padrão de cada empresa.
- [ ] **13.7** Atualizar o kanban: t30 e t31 passam para "Em revisão", junto com o novo card do bug do inventário (t46).

## Checagem de cobertura da spec

| Item da spec | Tarefa |
|---|---|
| 5.1 Depósito padrão | 2, 3 |
| 5.2 Ordem fixa de travas e lock_timeout | 7, 8 |
| 5.3 `processar()` | 8 |
| 5.4 Aprovação e transições | 9, 10, 11 |
| 5.5 Constraints e checagem prévia | 5 |
| 5.6 `verificar_saldos` | 4 |
| 6 Erros e mensagens | 1, 10 |
| 7 Testes de concorrência | 6, 8, 12 |
