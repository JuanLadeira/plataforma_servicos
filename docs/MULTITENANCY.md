# Arquitetura de Multitenancy

Este documento descreve a arquitetura de multitenancy implementada na plataforma, onde cada **Empresa** funciona como um tenant isolado com seus próprios dados.

## Visão Geral

A plataforma utiliza **multitenancy lógico** com banco de dados compartilhado. Cada empresa possui seus dados segregados (produtos, inventário, pedidos, corretores, etc.) identificados por uma Foreign Key para o modelo `Empresa`.

### Estrutura de Administração

A plataforma possui **dois níveis de administração**:

| Admin | URL | Acesso | Função |
|-------|-----|--------|--------|
| **Admin Principal** | `localhost:8000/admin/` | Superusuários | Gerenciar empresas, configurações globais |
| **Admin da Empresa** | `empresa.dominio.com/{admin_url}/` | Funcionários da empresa | Gerenciar dados da empresa (produtos, pedidos, etc.) |

### Identificação do Tenant

| Contexto | Identificação |
|----------|---------------|
| URLs públicas (vitrine) | Subdomínio (`empresa-slug.dominio.com`) |
| Admin da empresa | Subdomínio + usuário autenticado |
| Admin principal | Apenas domínio principal (sem subdomínio) |

---

## Arquitetura de Componentes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Request HTTP                                   │
│                                                                             │
│  Domínio Principal          │         Subdomínio Empresa                    │
│  localhost:8000             │         empresa.dominio.com                   │
└─────────────────────────────┴───────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TenantMiddleware                                  │
│              plataforma_de_servicos/core/middleware/tenant.py               │
│                                                                             │
│  • Identifica se é domínio principal ou subdomínio                          │
│  • /admin/ só acessível no domínio principal                                │
│  • Subdomínio: extrai tenant do slug                                        │
│  • Injeta request.tenant e request.is_main_domain                           │
└─────────────────────────────────────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AdminUrlRewriteMiddleware                              │
│         plataforma_de_servicos/core/middleware/admin_url_rewrite.py         │
│                                                                             │
│  • Reescreve URL customizada do admin para /gerentes/                       │
│  • Ex: /painel-admin/ → /gerentes/ (internamente)                           │
└─────────────────────────────────────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
┌──────────────────────────┐         ┌────────────────────────────────────────┐
│     Admin Principal      │         │           Admin da Empresa             │
│      /admin/             │         │    /{admin_url}/ (padrão: /gerentes/)  │
│                          │         │                                        │
│  • CRUD de Empresas      │         │  • Produtos, Categorias                │
│  • Configurações globais │         │  • Inventário, Estoque                 │
│  • Usuários sistema      │         │  • Pedidos, Corretores                 │
└──────────────────────────┘         └────────────────────────────────────────┘
```

---

## Modelo Empresa

```python
class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # Usado no subdomínio
    email = models.EmailField()
    imo = models.CharField(max_length=100)
    foto = models.ImageField(blank=True, null=True)

    # URL customizável do admin
    admin_url = models.CharField(
        max_length=50,
        default="gerentes",
        help_text="Endpoint do painel administrativo (ex: 'gerentes' → /gerentes/)"
    )
```

### Campo `admin_url`

Cada empresa pode customizar o endpoint do seu painel administrativo:

| Empresa | `admin_url` | URL Final |
|---------|-------------|-----------|
| Pizzaria João | `gerentes` (padrão) | `pizzaria-joao.dominio.com/gerentes/` |
| Loja Maria | `painel` | `loja-maria.dominio.com/painel/` |
| Mercado José | `admin-loja` | `mercado-jose.dominio.com/admin-loja/` |

---

## Modelos com Suporte a Multitenancy

| Modelo | App | Constraint |
|--------|-----|------------|
| `Funcionario` | users | empresa FK |
| `Categoria` | produto | unique_together(empresa, categoria) |
| `Produto` | produto | unique_together(empresa, produto) |
| `Atributo` | produto | unique_together(empresa, nome) |
| `Inventario` | inventario | unique_together(empresa, nome) |
| `Estoque` | estoque | empresa FK |
| `Corretor` | corretor | unique_together(empresa, email) |
| `InteresseCompra` | corretor | empresa FK |
| `OrdemCompra` | vendas | unique_together(empresa, numero) |
| `Order` | payment | empresa FK |
| `Carrinho` | servico | unique_together(empresa, slug) |

### Modelos que Herdam Tenant (via FK pai)

- `VariacaoProduto` → herda de `Produto.empresa`
- `ValorAtributo` → herda de `Atributo.empresa`
- `InventarioSaldo` → herda de `Inventario.empresa`
- `EstoqueItens` → herda de `Estoque.empresa`
- `ItemOrdemCompra` → herda de `OrdemCompra.empresa`
- `ItemInteresse` → herda de `InteresseCompra.empresa`
- `Image` (produto) → herda de `Produto.empresa`

---

## Componentes Principais

### 1. TenantMiddleware

**Arquivo:** `plataforma_de_servicos/core/middleware/tenant.py`

```python
class TenantMiddleware:
    def __call__(self, request):
        request.tenant = None
        request.is_main_domain = False

        # Determina se é domínio principal
        is_main_domain = self._is_main_domain(request)
        request.is_main_domain = is_main_domain

        # /admin/ só acessível no domínio principal
        if request.path.startswith("/admin/"):
            if not is_main_domain:
                raise Http404("Página não encontrada")
            return self.get_response(request)

        # Subdomínio: identifica tenant
        if not is_main_domain:
            request.tenant = self._get_tenant_from_subdomain(request)

        return self.get_response(request)
```

### 2. AdminUrlRewriteMiddleware

**Arquivo:** `plataforma_de_servicos/core/middleware/admin_url_rewrite.py`

Reescreve URLs do admin customizado para `/gerentes/`:

```python
class AdminUrlRewriteMiddleware:
    def __call__(self, request):
        tenant = getattr(request, "tenant", None)
        if not tenant:
            return self.get_response(request)

        admin_url = tenant.admin_url
        if admin_url != "gerentes":
            custom_path = f"/{admin_url}/"
            if request.path.startswith(custom_path):
                # Reescreve /painel/ para /gerentes/
                request.path = request.path.replace(custom_path, "/gerentes/", 1)
                request.path_info = request.path

        return self.get_response(request)
```

### 3. TenantAwareAdminMixin

**Arquivo:** `plataforma_de_servicos/core/admin/mixins.py`

Usado nas classes Admin para filtrar por tenant:

```python
class TenantAwareAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.tenant and hasattr(self.model, 'empresa'):
            return qs.filter(empresa=request.tenant)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, 'empresa') and not obj.empresa_id:
            obj.empresa = request.tenant
        super().save_model(request, obj, form, change)
```

### 4. Cart com Isolamento por Tenant

**Arquivo:** `plataforma_de_servicos/cart/cart.py`

```python
class Cart:
    def __init__(self, request):
        self.tenant = getattr(request, "tenant", None)
        self.cart_key = f"cart_{self.tenant.slug}" if self.tenant else "cart"
```

---

## Guia de Configuração

### 1. Cadastrar uma Empresa (Admin Principal)

1. Acesse o **Admin Principal**: `http://localhost:8000/admin/`
2. Faça login como **superusuário**
3. Vá em **Empresa > Empresas > Adicionar**
4. Preencha os campos:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| Nome | Nome da empresa | "Pizzaria do João" |
| Slug | Identificador para URL (subdomínio) | "pizzaria-joao" |
| Email | Email de contato | "contato@pizzaria.com" |
| IMO | Código identificador | "123456" |
| URL do Admin | Endpoint do painel (opcional) | "gerentes" ou "painel" |
| Foto | Logo da empresa (opcional) | - |

5. Salve a empresa

**Resultado:** A empresa estará acessível em `pizzaria-joao.seudominio.com`

### 2. Via Django Shell

```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py shell_plus
```

```python
from plataforma_de_servicos.empresa.models import Empresa

# Criar empresa com admin customizado
empresa = Empresa.objects.create(
    nome="Pizzaria do João",
    slug="pizzaria-joao",
    email="contato@pizzariajoao.com",
    imo="123456",
    admin_url="painel"  # Admin será em /painel/ ao invés de /gerentes/
)
print(f"Empresa: {empresa.nome}")
print(f"Vitrine: https://{empresa.slug}.seudominio.com/")
print(f"Admin: https://{empresa.slug}.seudominio.com{empresa.get_admin_url()}")
```

### 3. Criar Funcionário para a Empresa

```python
from django.contrib.auth import get_user_model
from plataforma_de_servicos.users.models import Funcionario

User = get_user_model()

# Criar usuário
user = User.objects.create_user(
    email="gerente@pizzariajoao.com",
    password="senha123",
    name="Gerente João",
    user_type="FUNCIONARIO"
)

# Criar funcionário vinculado à empresa
funcionario = Funcionario.objects.create(
    usuario=user,
    empresa=empresa,
    cargo="Gerente",
    cpf="12345678901"
)
```

### 4. Configurar Dados Iniciais da Empresa

```python
from plataforma_de_servicos.produto.models import Categoria, Produto, Atributo, ValorAtributo
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.inventario.models import Inventario, InventarioSaldo

# Criar categoria
categoria = Categoria.objects.create(
    empresa=empresa,
    categoria="Pizzas Tradicionais"
)

# Criar atributo
atributo_tamanho = Atributo.objects.create(
    empresa=empresa,
    nome="Tamanho"
)

# Criar valores do atributo
valor_p = ValorAtributo.objects.create(atributo=atributo_tamanho, valor="Pequena")
valor_m = ValorAtributo.objects.create(atributo=atributo_tamanho, valor="Média", preco_adicional=10)
valor_g = ValorAtributo.objects.create(atributo=atributo_tamanho, valor="Grande", preco_adicional=20)

# Criar inventário com vitrine habilitada
inventario = Inventario.objects.create(
    empresa=empresa,
    nome="Loja Principal",
    is_ativo=True,
    exibir_na_vitrine=True  # IMPORTANTE: necessário para aparecer na home
)

# Criar produto
produto = Produto.objects.create(
    empresa=empresa,
    produto="Pizza Margherita",
    categoria=categoria,
    preco=45.00,
    estoque=100,
    disponivel=True
)

# Criar variação do produto (necessário para aparecer na vitrine)
variacao = VariacaoProduto.objects.create(
    produto=produto,
    preco=45.00,
    estoque=100
)
variacao.valores.add(valor_m)
variacao.gerar_sku()
variacao.save()

# Criar saldo no inventário
InventarioSaldo.objects.create(
    inventario=inventario,
    produto=produto,
    quantidade=100
)

print("Configuração completa!")
```

---

## Testando Localmente

### Passo 1: Configurar /etc/hosts

```bash
sudo nano /etc/hosts
```

Adicione:

```
127.0.0.1   pizzaria-joao.localhost
127.0.0.1   loja-maria.localhost
```

### Passo 2: Atualizar ALLOWED_HOSTS

Em `config/settings/local.py`:

```python
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    ".localhost",  # Wildcard para subdomínios
]
```

### Passo 3: Acessar os Sites

| URL | Função |
|-----|--------|
| `http://localhost:8000/admin/` | Admin Principal (gerenciar empresas) |
| `http://pizzaria-joao.localhost:8000/` | Vitrine da Pizzaria |
| `http://pizzaria-joao.localhost:8000/gerentes/` | Admin da Pizzaria (padrão) |
| `http://pizzaria-joao.localhost:8000/painel/` | Admin da Pizzaria (se admin_url="painel") |
| `http://loja-maria.localhost:8000/` | Vitrine da Loja Maria |

### Verificação de Isolamento

```bash
# Tentar acessar /admin/ pelo subdomínio deve retornar 404
curl -I http://pizzaria-joao.localhost:8000/admin/
# HTTP/1.1 404 Not Found

# Admin principal só funciona no domínio sem subdomínio
curl -I http://localhost:8000/admin/
# HTTP/1.1 200 OK (ou 302 redirect para login)
```

---

## Fluxo de Requisições

### Vitrine Pública

```
1. Usuário acessa: http://pizzaria-joao.localhost:8000/

2. TenantMiddleware:
   - Host: "pizzaria-joao.localhost"
   - Extrai slug: "pizzaria-joao"
   - Busca: Empresa.objects.get(slug="pizzaria-joao")
   - Define: request.tenant = <Empresa: Pizzaria do João>
   - Define: request.is_main_domain = False

3. View home():
   - Filtra: ProdutoService.listar_variacoes_vitrine(empresa=request.tenant)
   - Retorna apenas produtos da Pizzaria

4. Renderiza vitrine com produtos filtrados
```

### Admin da Empresa (URL customizada)

```
1. Funcionário acessa: http://pizzaria-joao.localhost:8000/painel/

2. TenantMiddleware:
   - Identifica tenant: Pizzaria do João
   - tenant.admin_url = "painel"

3. AdminUrlRewriteMiddleware:
   - Path original: /painel/produto/
   - Reescreve para: /gerentes/produto/

4. GerenteAdminSite:
   - Verifica permissão do funcionário
   - Filtra queryset por request.tenant
   - Renderiza admin com dados da Pizzaria
```

### Admin Principal

```
1. Superusuário acessa: http://localhost:8000/admin/

2. TenantMiddleware:
   - Host: "localhost"
   - is_main_domain = True
   - request.tenant = None (não definido)

3. Django Admin padrão:
   - Exibe todas as empresas
   - CRUD completo de Empresa
```

---

## Configuração para Produção

### DNS Wildcard

```
*.seudominio.com.br  →  IP_DO_SERVIDOR
seudominio.com.br    →  IP_DO_SERVIDOR  (admin principal)
```

### Traefik

```yaml
labels:
  - "traefik.http.routers.django.rule=HostRegexp(`{subdomain:[a-z0-9-]+}.seudominio.com.br`) || Host(`seudominio.com.br`)"
  - "traefik.http.routers.django.entrypoints=websecure"
  - "traefik.http.routers.django.tls.certresolver=letsencrypt"
```

### ALLOWED_HOSTS

```python
# config/settings/production.py
ALLOWED_HOSTS = [
    "seudominio.com.br",      # Domínio principal (admin)
    ".seudominio.com.br",     # Wildcard para subdomínios
]
```

---

## Troubleshooting

### /admin/ retorna 404 no subdomínio

**Comportamento esperado!** O `/admin/` principal só é acessível no domínio principal (sem subdomínio). No subdomínio, use a URL do admin da empresa (`/gerentes/` ou a URL customizada).

### Funcionário não consegue acessar o admin da empresa

1. Verifique se o funcionário está vinculado à empresa:
```python
funcionario = Funcionario.objects.get(usuario__email="gerente@empresa.com")
print(funcionario.empresa)  # Deve mostrar a empresa
```

2. Verifique se está acessando pelo subdomínio correto.

### Vitrine vazia mesmo com produtos cadastrados

Checklist:
- [ ] Produto tem `empresa` definida
- [ ] Produto tem `disponivel=True`
- [ ] Produto tem pelo menos uma `VariacaoProduto` com `estoque > 0`
- [ ] Existe `Inventario` com `exibir_na_vitrine=True`
- [ ] Existe `InventarioSaldo` para o produto nesse inventário

```python
# Debug completo
produto = Produto.objects.get(id=1)
print(f"Empresa: {produto.empresa}")
print(f"Disponível: {produto.disponivel}")
print(f"Variações com estoque: {produto.variacoes.filter(estoque__gt=0).count()}")

inventarios = Inventario.objects.filter(
    empresa=produto.empresa,
    exibir_na_vitrine=True,
    is_ativo=True
)
print(f"Inventários vitrine: {list(inventarios)}")

saldos = InventarioSaldo.objects.filter(
    produto=produto,
    inventario__exibir_na_vitrine=True,
    quantidade__gt=0
)
print(f"Saldos em vitrine: {list(saldos)}")
```

---

## Referências de Código

| Componente | Arquivo |
|------------|---------|
| TenantMiddleware | `plataforma_de_servicos/core/middleware/tenant.py` |
| AdminUrlRewriteMiddleware | `plataforma_de_servicos/core/middleware/admin_url_rewrite.py` |
| TenantAwareAdminMixin | `plataforma_de_servicos/core/admin/mixins.py` |
| Modelo Empresa | `plataforma_de_servicos/empresa/models.py` |
| EmpresaAdmin | `plataforma_de_servicos/empresa/admin.py` |
| GerenteAdminSite | `plataforma_de_servicos/core/admin/sites/gerente_admin_site.py` |
| ProdutoService | `plataforma_de_servicos/produto/services/produto_service.py` |
| Home View | `plataforma_de_servicos/produto/views/views.py` |
| Cart | `plataforma_de_servicos/cart/cart.py` |
| Testes Multitenancy | `plataforma_de_servicos/inventario/tests/test_home_vitrine.py` |
