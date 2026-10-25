# Plataforma de Serviços

Plataforma **multi-empresa (multi-tenant)** de vitrine online e gestão comercial, construída em Django. Cada empresa cliente ganha a sua própria loja num subdomínio (`empresa.dominio.com`), com tema visual próprio, catálogo de produtos com variações, controle de estoque em vários depósitos e um portal interno para gerentes e vendedores.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

---

## Sumário

- [O que a plataforma faz](#o-que-a-plataforma-faz)
- [Como funciona no geral](#como-funciona-no-geral)
- [Arquitetura](#arquitetura)
  - [Stack](#stack)
  - [Apps Django](#apps-django)
  - [Multi-tenancy por subdomínio](#multi-tenancy-por-subdomínio)
  - [Portais administrativos](#portais-administrativos)
  - [Fluxo de vendas: lead → ordem → comissão](#fluxo-de-vendas-lead--ordem--comissão)
  - [Estoque e inventário](#estoque-e-inventário)
  - [Temas por empresa](#temas-por-empresa)
- [Como rodar localmente](#como-rodar-localmente)
- [Testes e qualidade de código](#testes-e-qualidade-de-código)
- [Como contribuir](#como-contribuir)
- [Documentação adicional](#documentação-adicional)

---

## O que a plataforma faz

A ideia é que uma única instalação atenda várias empresas independentes, como uma concessionária, uma mercearia e um ateliê de artigos religiosos, sem que uma veja os dados da outra.

Para o **cliente final**, cada empresa tem uma vitrine pública onde ele navega por categorias, vê produtos e suas variações (cor, tamanho, modelo...), monta um carrinho e envia um **pedido de interesse**. Não há pagamento online: o pedido vira um *lead* que um vendedor da empresa vai atender.

Para a **empresa**, há um portal de gestão onde ela:

- cadastra categorias, atributos, produtos, imagens e variações (SKU);
- controla o estoque em um ou mais depósitos, com entradas, saídas e transferências;
- distribui e atende os leads que chegam pela vitrine;
- transforma leads em ordens de compra, aprova, fatura e conclui;
- calcula e acompanha as comissões dos vendedores;
- personaliza o nome, logo, banner e tema de cores da sua loja.

Para o **dono da plataforma** (superusuário), o admin principal permite criar empresas e administrar tudo de forma global.

## Como funciona no geral

```
 Cliente                       Empresa (gerentes / vendedores)
 ───────                       ───────────────────────────────
 acessa empresa.dominio.com
   │
   ▼
 vitrine (tema da empresa)
   │  navega, escolhe variação
   ▼
 carrinho (sessão)
   │  envia pedido de interesse
   ▼
 InteresseCompra (NOVO) ─────────▶ vendedor recebe e-mail, assume o lead
                                     │  EM_ATENDIMENTO
                                     ▼
                                   converte o lead (CONVERTIDO)
                                     │  signal cria a OrdemCompra
                                     ▼
                                   OrdemCompra (PENDENTE_APROVACAO)
                                     │  gerente aprova:
                                     │  baixa o estoque + gera Comissao
                                     ▼
                                   APROVADA → FATURADA → CONCLUIDA
```

1. A requisição chega e o `TenantMiddleware` descobre de qual empresa ela é (pelo subdomínio ou pelo usuário logado) e coloca essa empresa em `request.tenant`.
2. As views, os admins e os serviços filtram tudo por `empresa=request.tenant`.
3. O context processor carrega o `SiteConfig` da empresa e injeta o tema como variáveis CSS no `base.html`.
4. A interação da vitrine usa **htmx**: as views devolvem fragmentos de template quando recebem o cabeçalho `HX-Request`, e disparam eventos como `cartUpdated`, `showToast` e `openCartOffcanvas`.
5. Tarefas demoradas, como o envio de e-mail de novo lead, rodam no **Celery** com Redis como broker.

## Arquitetura

### Stack

| Camada | Tecnologias |
|---|---|
| Backend | Python 3.12, Django 5.1, Django REST Framework |
| Banco de dados | PostgreSQL (driver psycopg 3) |
| Frontend | Templates Django, htmx, Bootstrap 5, crispy-forms |
| Admin | django-unfold, com dois admin sites próprios (gerentes e vendedores) |
| Autenticação | django-allauth (login por e-mail, MFA), django-guardian |
| Tarefas assíncronas | Celery, Redis, django-celery-beat, Flower |
| E-mail em dev | Mailpit |
| Testes | pytest, pytest-django, factory-boy |
| Qualidade | ruff, mypy (django-stubs), djLint, pre-commit |
| Infra | Docker Compose, `just` |

O projeto nasceu do [cookiecutter-django](https://github.com/cookiecutter/cookiecutter-django), então a organização de `config/settings`, `compose/` e `requirements/` segue esse padrão.

### Estrutura de pastas

```
config/                    settings (base, local, test, production), urls, celery_app
compose/                   Dockerfiles e scripts de start (local e produção)
requirements/              base.txt, local.txt, production.txt
plataforma_de_servicos/    código da aplicação (um diretório por app)
  templates/               templates (base.html, pages/, partials/ para htmx)
  static/                  css (theme.css, project.css), js, imagens
docs/                      documentação técnica (Sphinx) e specs de features
```

### Apps Django

Todos ficam em `plataforma_de_servicos/`.

| App | Responsabilidade | Modelos principais |
|---|---|---|
| `core` | Middlewares, admin sites, mixins tenant-aware, temas, context processors, comandos de seed | `SiteConfig`, `TimeStampedModel` |
| `empresa` | Cadastro das empresas (tenants) | `Empresa` |
| `users` | Usuário customizado (login por e-mail) e perfis | `User`, `Funcionario`, `Cliente` |
| `account` | Telas de conta do usuário | |
| `produto` | Catálogo: categorias, atributos, produtos, imagens, variações | `Categoria`, `Produto`, `Atributo`, `ValorAtributo`, `VariacaoProduto` |
| `inventario` | Depósitos e saldo por depósito | `Inventario`, `InventarioSaldo` |
| `estoque` | Movimentações de estoque (entrada, saída, transferência) | `Estoque`, `EstoqueItens` |
| `cart` | Carrinho de compras guardado na sessão | (sessão) |
| `corretor` | Leads gerados pela vitrine e seu atendimento | `InteresseCompra`, `ItemInteresse` |
| `vendas` | Ordens de compra e comissões | `OrdemCompra`, `ItemOrdemCompra`, `Comissao`, `ConfiguracaoComissao` |

As regras de negócio ficam em **camadas de serviço** (`services.py` ou `services/`), por exemplo `InteresseCompraService`, `OrdemCompraService`, `CommissionService` e `EstoqueService`. Views e admins chamam esses serviços em vez de manipular os modelos diretamente.

### Multi-tenancy por subdomínio

O isolamento é **lógico, em banco compartilhado**: cada modelo de negócio tem uma FK para `Empresa` (ou chega a ela por uma relação, como `VariacaoProduto → Produto → Empresa`).

O `TenantMiddleware` (`core/middleware/tenant.py`) resolve a empresa nesta ordem:

1. **Subdomínio**: `autoprime.dominio.com`, `autoprime.localhost` ou `autoprime.lvh.me` apontam para a empresa de slug `autoprime`. Um usuário logado de outra empresa recebe 403.
2. **Usuário logado**: nos portais (`/gerentes/`, `/vendedores/`, `/estoque/api/`) acessados pelo domínio principal, a empresa vem do perfil `Funcionario` do usuário.
3. **Apenas com `DEBUG=True`**: `?tenant=<slug>` na URL, que fica guardado na sessão. Útil para testar sem configurar subdomínios.

O `/admin/` só abre no domínio principal e não aplica filtro de empresa.

No admin, o `TenantAwareAdminMixin` (`core/admin/mixins.py`) filtra os querysets por `request.tenant`, preenche `empresa` automaticamente ao criar registros e restringe as opções de FK/M2M à empresa atual. O teste `core/tests/test_isolamento_parametrico.py` percorre todos os admins e views e garante que uma empresa nunca vê dados de outra.

> O `docs/MULTITENANCY.md` detalha os componentes e o fluxo da requisição.

### Portais administrativos

| Portal | URL | Quem usa | Escopo |
|---|---|---|---|
| Admin principal | `/admin/` | Superusuário da plataforma | Tudo, sem filtro de empresa |
| Gerentes | `/gerentes/` | Gerentes da empresa | Dados da própria empresa |
| Vendedores | `/vendedores/` | Vendedores (corretores) | Leads, ordens e comissões da própria empresa |

Cada empresa pode trocar o caminho dos portais pelos campos `admin_url` e `vendedor_url` do modelo `Empresa`; o `AdminUrlRewriteMiddleware` faz o mapeamento.

### Fluxo de vendas: lead → ordem → comissão

**1. `InteresseCompra` (lead)** — criado quando o cliente envia o carrinho. Os vendedores ativos recebem e-mail (task Celery).

| Status | Significado |
|---|---|
| `NOVO` | Chegou pela vitrine, ainda sem vendedor |
| `EM_ATENDIMENTO` | Um vendedor assumiu (`InteresseCompraService.atender`) |
| `CONVERTIDO` | Virou venda (`converter`) |
| `DESCARTADO` | Não seguiu adiante (`descartar`) |

**2. `OrdemCompra`** — quando o lead passa para `CONVERTIDO`, o signal `vendas/signals.py` chama `OrdemCompraService.criar_ordem_de_interesse`. Também é possível criar ordens manualmente.

| Status | O que acontece |
|---|---|
| `PENDENTE_APROVACAO` | Ordem criada, aguardando o gerente |
| `APROVADA` | Numa única transação: valida e baixa o estoque do depósito padrão, muda o status e gera a comissão |
| `REJEITADA` | Gerente recusou, com motivo |
| `FATURADA` | Ordem faturada |
| `CONCLUIDA` | Venda encerrada |
| `CANCELADA` | Cancelada |

**3. `Comissao`** — calculada pelo `CommissionService` a partir da `ConfiguracaoComissao` da empresa, com percentuais que podem variar por categoria (`ComissaoCategoria`) e por vendedor (`ComissaoVendedor`). Status: `PENDENTE → APROVADA → PAGA`, ou `CANCELADA`.

### Estoque e inventário

- `Inventario` é um depósito da empresa; `InventarioSaldo` guarda a quantidade de cada produto/variação em cada depósito.
- Toda alteração de saldo passa por uma movimentação `Estoque` (`E` entrada, `S` saída, `T` transferência) com seus `EstoqueItens`.
- O processamento é atômico e trava as linhas de saldo (`select_for_update`), para que duas aprovações simultâneas não deixem o saldo negativo.
- O comando `verificar_saldos` lista saldos negativos, duplicados ou divergentes; com `--corrigir`, consolida e recalcula.

### Temas por empresa

Cada empresa tem um `SiteConfig` com nome do site, logo, textos e imagem do banner e um dos temas definidos em `core/themes.py` (`default`, `dark`, `nature`, `luxury`, `energy`, `axe`, `ocean`, `rose`, `earth`, `minimal`, `gatopreto`, `mystic`).

O tema vira um conjunto de variáveis CSS (`--color-primary`, `--color-bg`, `--color-navbar-bg`...) aplicado no `<body>` do `base.html`. Os componentes em `static/css/theme.css` usam apenas essas variáveis, então trocar o tema no admin muda a loja inteira sem deploy.

## Como rodar localmente

### Pré-requisitos

- Docker e Docker Compose
- [`just`](https://github.com/casey/just) (opcional, mas os atalhos abaixo usam ele)

### 1. Variáveis de ambiente

O `docker-compose.local.yml` lê `.envs/.local/.django` e `.envs/.local/.postgres`, que já estão versionados com valores de desenvolvimento. Ajuste se precisar (por exemplo, chaves de APIs externas). Nunca coloque segredos de produção nesses arquivos.

### 2. Subir os containers

```bash
just build     # constrói as imagens
just up        # sobe django, postgres, redis, mailpit, celeryworker, celerybeat e flower
just logs django
```

As migrations rodam automaticamente quando o container `django` inicia.

| Serviço | Endereço |
|---|---|
| Aplicação | http://localhost:8000 |
| Mailpit (e-mails enviados) | http://localhost:8025 |
| Flower (monitor do Celery) | http://localhost:5555 |

Sem `just`, use `docker compose -f docker-compose.local.yml <comando>`. O `pyproject.toml` também tem atalhos via taskipy (`task up`, `task test`, `task logs`).

### 3. Criar dados de exemplo

```bash
just manage createsuperuser
just manage seed_completo          # empresas autoprime, autolitros e gatopreto
just manage seed_completo --clear  # apaga e recria os dados dessas empresas
```

O `seed_completo` cria as empresas com categorias, produtos, depósitos, estoque, funcionários, leads, ordens e comissões. Os usuários criados usam a senha `teste123` e são listados ao final do comando (por exemplo, `carlos.silva@autoprime.com.br`).

### 4. Acessar como uma empresa

Os navegadores resolvem `*.localhost` para `127.0.0.1`, então basta abrir:

- Vitrine: http://autoprime.localhost:8000/
- Portal de gerentes: http://autoprime.localhost:8000/gerentes/
- Portal de vendedores: http://autoprime.localhost:8000/vendedores/
- Admin principal (só no domínio principal): http://localhost:8000/admin/

Alternativas: `http://autoprime.lvh.me:8000/` ou, com `DEBUG=True`, `http://localhost:8000/?tenant=autoprime`.

### Celery

Os containers `celeryworker` e `celerybeat` já sobem com `just up`. Para rodar fora do Docker, a partir da pasta do `manage.py`:

```bash
celery -A config.celery_app worker -l info
celery -A config.celery_app beat
```

## Testes e qualidade de código

```bash
# toda a suíte
docker compose -f docker-compose.local.yml run --rm django pytest

# um app específico
docker compose -f docker-compose.local.yml run --rm django pytest plataforma_de_servicos/vendas/

# por marcador (ver [tool.pytest.ini_options] no pyproject.toml)
docker compose -f docker-compose.local.yml run --rm django pytest -m estoque

# cobertura
docker compose -f docker-compose.local.yml run --rm django coverage run -m pytest
docker compose -f docker-compose.local.yml run --rm django coverage html
```

Os testes usam `config.settings.test`, onde o Celery roda em modo *eager* (sem precisar de broker).

Qualidade de código:

```bash
pre-commit install      # roda ruff, ruff-format e djLint a cada commit
ruff check <arquivos>
ruff format <arquivos>
mypy plataforma_de_servicos
djlint plataforma_de_servicos/templates --check
```

O repositório ainda tem muitos avisos de ruff herdados. Aplique `ruff --fix`/`ruff format` apenas nos arquivos que você alterou, para não poluir o diff com mudanças não relacionadas.

## Como contribuir

1. **Abra ou escolha uma issue** descrevendo o problema ou a funcionalidade.
2. **Para mudanças maiores, escreva primeiro a spec e o plano** em `docs/superpowers/specs/` (veja os exemplos `*-design.md` e `*-plano.md`) e combine a abordagem antes de implementar.
3. **Crie uma branch** a partir da `main` (`feat/<nome>`, `fix/<nome>`, `docs/<nome>`).
4. **Implemente com testes.** Toda regra de negócio nova deve ter teste em `<app>/tests/`; use as factories do factory-boy.
5. **Respeite as convenções do projeto:**
   - lógica de negócio em serviços, não em views ou signals;
   - toda query em contexto de empresa filtra por `empresa`; um modelo novo exposto nos portais deve entrar no teste de isolamento paramétrico;
   - admins dos portais usam `TenantAwareAdminMixin`;
   - movimentação de estoque sempre por `Estoque`/`EstoqueService`, dentro de `transaction.atomic`;
   - modelos novos herdam de `TimeStampedModel`;
   - código, nomes de domínio e mensagens em português, seguindo o que já existe.
6. **Rode os testes e o pre-commit** antes de abrir o PR.
7. **Abra o Pull Request** para a `main` explicando o quê e o porquê, com o link da issue. Se houver migration que exija passo manual no deploy, descreva no PR.

Commits seguem o estilo [Conventional Commits](https://www.conventionalcommits.org/pt-br/) em português, por exemplo `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`.

## Documentação adicional

| Arquivo | Conteúdo |
|---|---|
| `docs/MULTITENANCY.md` | Detalhes da arquitetura multi-tenant |
| `docs/superpowers/specs/` | Specs e planos de implementação de features |
| `CLAUDE.md` | Contexto do projeto para assistentes de código |
| `TESTES_README.md`, `UI_TESTS_README.md` | Notas sobre a suíte de testes (podem estar desatualizadas) |
