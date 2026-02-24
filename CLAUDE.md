# Claude Context: plataforma_de_servicos

## Project Overview

This is a Django 5.1.7-based **multi-tenant e-commerce platform** named `plataforma_de_servicos`. The project features sophisticated inventory management, product catalog with variations and attributes, shopping cart functionality, user authentication, and a dynamic theming system for per-company customization.

**Key Differentiators:**
- **Multi-tenancy:** Subdomain-based tenant isolation with per-company theming
- **Multi-location inventory:** Atomic stock tracking across multiple warehouses
- **Product variations:** Comprehensive SKU-based variation management with attributes
- **Dynamic theming:** 12 pre-defined themes with CSS variables for instant customization

## Core Technologies

- **Backend:** Django 5.1.7, Django REST Framework 3.15.2
- **Database:** PostgreSQL (via psycopg[c] 3.2.4)
- **Frontend:** Django Templates, htmx, Bootstrap 5.2.3, Poppins font
- **Admin:** django-unfold 0.52.0 with custom admin sites (Gerente, Vendedor)
- **Task Queue:** Celery 5.4.0 + Redis + django-celery-beat 2.7.0
- **Authentication:** django-allauth 65.3.1 (email-based, MFA support)
- **AI/LLM:** langchain 0.3.23+, langchain-deepseek 0.1.3, OpenAI 1.72.0+
- **Testing:** pytest 8.3.4, pytest-django 4.9.0, factory-boy 3.3.1
- **Code Quality:** mypy 1.13.0, ruff 0.9.4, pre-commit 4.1.0

## Application Architecture

### Django Apps

| App | Purpose | Key Models |
|-----|---------|------------|
| **core** | Shared utilities, theming, middleware | `SiteConfig`, `TimeStampedModel` |
| **users** | Custom User model (email-based) | `User`, `Funcionario`, `Cliente` |
| **empresa** | Company/tenant management | `Empresa` |
| **produto** | Product catalog | `Produto`, `Categoria`, `Atributo`, `VariacaoProduto` |
| **estoque** | Stock movements | `Estoque`, `EstoqueItens`, `EstoqueEntrada`, `EstoqueSaida` |
| **inventario** | Multi-location inventory | `Inventario`, `InventarioSaldo` |
| **cart** | Session-based shopping cart | (session storage) |
| **corretor** | Broker/sales agent management | `InteresseCompra`, `ItemInteresse` |
| **vendas** | Orders and commissions | `OrdemCompra`, `Comissao`, `ConfiguracaoComissao` |

## Multi-Tenancy Architecture

### Tenant Detection (TenantMiddleware)

**Location:** `core/middleware/tenant.py`

**Detection Priority:**
1. **Subdomain:** `empresa-slug.localhost` or `empresa-slug.domain.com`
2. **User Association:** From authenticated user's funcionário/cliente profile
3. **Query Parameter:** `?tenant=slug` (development mode)
4. **Session Storage:** Cached tenant selection

**Access Control:**
- `/admin/` - Main domain only, no tenant filtering
- `/gerentes/` - Tenant from user or query param, filtered data
- `/vendedores/` - Tenant from user, filtered data
- Public URLs - Tenant from subdomain

### Tenant-Aware Admin

**Mixin:** `TenantAwareAdminMixin` in `core/admin/mixins.py`

- Auto-filters querysets by `request.tenant`
- Auto-populates `empresa` field on create
- Filters ForeignKey/M2M relationships by tenant

## Theme System

### Theme Definition

**Location:** `core/themes.py`

**Available Themes (12):**
| Name | Display Name | Style | Description |
|------|--------------|-------|-------------|
| default | Padrão | light | Classic blue, clean and professional |
| dark | Escuro | dark | Elegant dark, ideal for tech |
| nature | Natureza | light | Green tones, organic products |
| luxury | Luxo | dark | Gold and black, premium products |
| energy | Energia | light | Vibrant orange, dynamic |
| axe | Axé | light | Purple and gold, African religions |
| ocean | Oceano | light | Turquoise, freshness |
| rose | Rosa | light | Elegant pink, feminine |
| earth | Terra | light | Earthy tones, rustic |
| minimal | Minimalista | light | Black and white, clean |
| **gatopreto** | Gato Preto | dark | Gold and black, religious items |
| mystic | Místico | dark | Deep purple with gold, spiritual |

### Theme Data Flow

```
Request → TenantMiddleware → Context Processor (site_config)
    ↓
SiteConfig.get_config(empresa=request.tenant)
    ↓
Theme object with colors → CSS variables string
    ↓
base.html: <body style="{{ theme_css_vars }}">
    ↓
theme.css: Components use var(--color-primary), etc.
```

### CSS Variables

Defined in `static/css/theme.css`:
```css
--color-primary      /* Buttons, links, accents */
--color-secondary    /* Secondary elements */
--color-accent       /* Badges, highlights */
--color-bg           /* Main background */
--color-bg-secondary /* Card backgrounds */
--color-text         /* Primary text */
--color-text-muted   /* Secondary text */
--color-navbar-bg    /* Navbar background */
--color-navbar-text  /* Navbar text */
--color-footer-bg    /* Footer background */
--color-footer-text  /* Footer text */
```

### SiteConfig Model

**Location:** `core/models.py`

**Fields:**
- `empresa` - FK to Empresa (singleton per tenant)
- `site_name` - Title in navbar
- `logo` - Site logo image
- `theme` - CharField with THEME_CHOICES
- `hero_title`, `hero_description`, `hero_button_text` - Banner content
- `hero_image` / `hero_image_url` - Banner background

## Admin System Architecture

### Admin Sites

| Site | URL | Purpose | Access |
|------|-----|---------|--------|
| Main Admin | `/admin/` | Full system access | Superusers |
| Gerente | `/gerentes/` | Manager portal | Managers, tenant-filtered |
| Vendedor | `/vendedores/` | Sales portal | Sales agents, tenant-filtered |

### Key Admin Features

- **TenantAwareAdminMixin:** Auto-filters by tenant
- **Actions de Detalhe:** Custom buttons in change form (unfold `@action` decorator)
- **Autocomplete Fields:** Fast search for related models

## Key Data Models

### Product Hierarchy
```
Categoria (1) ──→ (N) Produto
                       ├──→ (N) Image (ordered)
                       └──→ (N) VariacaoProduto
                                 └──→ (M2M) ValorAtributo ──→ Atributo
```

### Inventory System
```
Inventario (1) ──→ (N) InventarioSaldo ←── (N) Produto
                       └── quantidade, atualizado_em

Estoque (stock movement)
├── movimento: E (entrada), S (saida), T (transferencia)
├── inventario_origem / inventario_destino
└──→ (N) EstoqueItens
```

### Sales Flow
```
InteresseCompra (lead)
├── status: NOVO → EM_ATENDIMENTO → CONVERTIDO/DESCARTADO
├── corretor (Funcionario)
└──→ (N) ItemInteresse
         ↓ (conversão)
OrdemCompra
├── status: PENDENTE → CONFIRMADA → EM_PREPARACAO → etc.
└──→ Comissao (vendedor commission)
```

## Frontend Architecture

### Template Structure
```
templates/
├── base.html                    # Main layout, theme injection
├── navbar.html                  # Navigation with site config
├── pages/
│   ├── home.html               # Homepage with hero section
│   ├── produto-detail.html     # Product detail
│   ├── includes/               # Reusable containers
│   ├── partials/               # HTMX-loaded fragments
│   └── components/             # UI components
```

### HTMX Integration

- Views check `HX-Request` header
- Return partial templates for AJAX requests
- Events: `showToast`, `openCartOffcanvas`, `cartUpdated`

### Static Assets
```
static/
├── css/
│   ├── project.css    # Project-specific styles
│   └── theme.css      # Dynamic theme variables (891 lines)
├── js/
│   └── project.js     # Project JavaScript
└── images/            # Favicons, icons
```

## Development Workflow

### Docker Commands

```bash
# Using justfile
just build          # Build images
just up             # Start containers
just down           # Stop containers
just logs [service] # View logs
just manage <cmd>   # Django management command

# Using taskipy
task up / task down / task test / task logs
```

### Service Containers

| Service | Port | Purpose |
|---------|------|---------|
| django | 8000 | Main application |
| postgres | 5432 | Database |
| redis | 6379 | Cache/Celery broker |
| mailpit | 8025 | Email testing |
| celeryworker | - | Background tasks |
| celerybeat | - | Scheduled tasks |
| flower | 5555 | Celery monitoring |

### Testing

```bash
# Run all tests
docker compose -f docker-compose.local.yml run --rm django pytest

# With coverage
docker compose -f docker-compose.local.yml run --rm django pytest --cov

# Specific module
docker compose -f docker-compose.local.yml run --rm django pytest plataforma_de_servicos/corretor/tests/
```

### Code Quality

```bash
ruff check .           # Linting
ruff format .          # Formatting
mypy plataforma_de_servicos  # Type checking
djlint templates/      # Template linting
```

## Important Patterns

1. **TimeStampedModel:** Inherit from `core.models.TimeStampedModel` for auto timestamps

2. **AutoSlugField:** Used in Categoria, Produto, Atributo, Inventario

3. **Atomic Transactions:** Stock movements use `@transaction.atomic`

4. **Admin Inlines:** Use `autocomplete_fields` with `search_fields` defined

5. **Tenant Isolation:** Always filter by `empresa` in tenant-aware contexts

6. **Service Layer:** Business logic in services (e.g., `InteresseCompraService`)

## File Reference

| Purpose | Path |
|---------|------|
| Theme definitions | `core/themes.py` |
| Site config model | `core/models.py` |
| Tenant middleware | `core/middleware/tenant.py` |
| Admin mixins | `core/admin/mixins.py` |
| Gerente admin site | `core/admin/sites/gerente_admin_site.py` |
| Theme CSS | `static/css/theme.css` |
| Base template | `templates/base.html` |
| Home template | `templates/pages/home.html` |
| Context processor | `core/context_processors.py` |

## Known Technical Debt

1. **Legacy Store App:** `store.Product` still referenced by payment module
2. **Session Cart:** No persistence for logged-in users
3. **SKU Generation:** Requires manual call after M2M assignment

## Security Considerations

- LLM API keys in environment variables
- Email-based authentication with MFA support
- CSRF protection enabled
- Tenant isolation enforced at middleware level
- Object-level permissions via django-guardian

---

**Last Updated:** 2026-02-21
**Django Version:** 5.1.7
**Python Version:** 3.12.8
**Current Branch:** feat/multi-tenancy
