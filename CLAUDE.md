# Claude Context: plataforma_de_servicos

## Project Overview

This is a Django 5.1.7-based e-commerce and service platform named `plataforma_de_servicos`. The project features sophisticated inventory management, product catalog with variations and attributes, shopping cart functionality, user authentication, and payment processing. It uses Django REST Framework for APIs, django-unfold for a modern admin interface, and htmx for dynamic frontend interactions.

**Key Differentiator:** Multi-location inventory system with atomic stock tracking and comprehensive product variation management (SKU-based).

## Recent Issues Resolved

**✅ FIXED - Error:** `admin.E039` - An admin for model "ValorAtributo" has to be registered to be referenced by VariacaoProdutoInline.autocomplete_fields.

**Location:** `plataforma_de_servicos/produto/admin/gerente_admin.py` - VariacaoProdutoInline class

**Root Cause:** The `VariacaoProdutoInline` uses `autocomplete_fields = ['valores']` which references the `ValorAtributo` model, but this model was not registered in the gerente admin site.

**Solution Applied:**
1. Created `AtributoGerenteAdmin` and `ValorAtributoGerenteAdmin` classes in [gerente_admin.py](plataforma_de_servicos/produto/admin/gerente_admin.py)
2. Registered both `Atributo` and `ValorAtributo` models in [gerente_admin_site.py](plataforma_de_servicos/core/admin/sites/gerente_admin_site.py)
3. Added search capabilities with `search_fields = ["valor", "atributo__nome"]` for autocomplete functionality
4. System check now passes with no issues

**Status:** ✅ Resolved - Django system check passes successfully

## Core Technologies

- **Backend:** Django 5.1.7, Django REST Framework 3.15.2
- **Database:** PostgreSQL (via psycopg[c] 3.2.4)
- **Frontend:** Django Templates, htmx, Bootstrap, jQuery
- **Admin:** django-unfold 0.52.0 with custom "Gerente" admin site
- **Task Queue:** Celery 5.4.0 + Redis + django-celery-beat 2.7.0
- **Authentication:** django-allauth 65.3.1 (email-based, MFA support)
- **AI/LLM:** langchain 0.3.23+, langchain-deepseek 0.1.3, OpenAI 1.72.0+
- **Testing:** pytest 8.3.4, pytest-django 4.9.0, factory-boy 3.3.1
- **Code Quality:** mypy 1.13.0, ruff 0.9.4, pre-commit 4.1.0

## Application Architecture

### Django Apps

1. **users** - Custom User model (email-based) with roles (FUNCIONARIO/CLIENTE)
   - `User`: AbstractUser with email as USERNAME_FIELD
   - `Funcionario`: Employee profile (cargo, cpf, is_signatario)
   - `Cliente`: Customer profile (linked to Empresa)

2. **empresa** - Company/Organization management
   - `Empresa`: nome, slug, email, imo, foto

3. **produto** - Product catalog system
   - `Categoria`: categoria, slug
   - `Produto`: produto, slug, preco, estoque, categoria, images
   - `Image`: image, order (ordered by product)
   - `Atributo`: nome, slug (e.g., "Cor", "Tamanho")
   - `ValorAtributo`: valor, atributo (e.g., "Vermelho", "GG")
   - `VariacaoProduto`: sku (auto-generated), preco, estoque, valores (M2M to ValorAtributo)

4. **estoque** - Stock movement tracking
   - `Estoque`: movimento (E/S/T), nf, processado, inventario_origem/destino
   - `EstoqueItens`: produto, quantidade, saldo, inventario
   - Proxy models: `EstoqueEntrada`, `EstoqueSaida`

5. **inventario** - Multi-location inventory
   - `Inventario`: nome, slug, is_ativo
   - `InventarioSaldo`: quantidade, atualizado_em, inventario, produto

6. **cart** - Session-based shopping cart
   - Session storage with variation IDs, quantities, and prices
   - No database models, uses Django sessions

7. **servico** - Service/Order lifecycle
   - `Carrinho`: identificador, status (carrinho→pendente_pagamento→pago→concluido)
   - `Item`: FK to Carrinho (minimal structure)

8. **payment** - Payment processing
   - `Order`: full_name, email, shipping_address, amount_paid
   - `OrderItem`: product, quantity, price
   - **Note:** References legacy `store.Product` model (potential issue)

9. **store** - Legacy product/category system
   - `Product`, `Category` models
   - Appears to be replaced by `produto` app

10. **core** - Shared utilities
    - `TimeStampedModel`: Abstract base with created/modified timestamps

11. **account** - Reserved for future account features (currently empty)

## Key Data Models & Relationships

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

Estoque (stock movement record)
├── movimento: E (entrada), S (saida), T (transferencia)
├── inventario_origem (nullable)
├── inventario_destino (nullable)
└──→ (N) EstoqueItens
         ├── produto
         ├── quantidade
         ├── saldo
         └── inventario
```

### User System
```
User
├── user_type: FUNCIONARIO | CLIENTE
├── email (USERNAME_FIELD)
└── name

    ├─→ (1:1) Funcionario
    │            ├── cargo
    │            ├── cpf (unique)
    │            └── is_signatario
    │
    └─→ (1:1) Cliente
                 └──→ Empresa
```

## Admin System Architecture

### Standard Admin Site (`/admin/`)
- Default Django admin with django-unfold theme
- Full access to all models

### Gerente Admin Site (`/gerentes/`)
- Custom `GerenteAdminSite` in `core/admin.py`
- Role-based access (only "gerente" group members)
- Focused interface for managers
- Currently registered models:
  - Produto, Categoria, Atributo
  - Inventario, Estoque
  - **Missing:** ValorAtributo (causes autocomplete_fields error)

## Known Issues & Technical Debt

1. **CRITICAL - Current Error:**
   - `ValorAtributo` not registered in gerente admin site
   - Causes admin.E039 error when using autocomplete_fields
   - Location: `produto/admin/gerente_admin.py`

2. **Dual Product Systems:**
   - `produto.Produto` (modern, actively used)
   - `store.Product` (legacy)
   - Payment module still references `store.Product`
   - Risk of import errors and data inconsistency

3. **Incomplete Relationships:**
   - `servico.Item` has no product reference
   - Carrinho lacks clear linkage to Produto
   - Cart implementation is session-based (no persistence for logged-in users)

4. **SKU Generation:**
   - Requires manual `gerar_sku()` call after M2M assignment
   - SKU depends on attribute value IDs (not stable if IDs change)
   - Needs second save after creating VariacaoProduto

5. **Stock Management:**
   - `Produto.estoque` vs `VariacaoProduto.estoque` relationship unclear
   - Potential race conditions in concurrent stock updates
   - No automated low-stock alerts

## Development Workflow

### Docker Commands (via justfile or taskipy)

**Using just:**
```bash
just build          # Build Docker images
just up             # Start containers
just down           # Stop containers
just logs [service] # View logs
just manage <cmd>   # Run Django management command
```

**Using taskipy:**
```bash
task up             # Start containers
task down           # Stop containers
task test           # Run pytest
task logs           # Follow Django logs
task manage <cmd>   # Run management command
```

### Service Containers
- `django` (port 8000): Main application
- `postgres`: Database
- `redis`: Cache and Celery broker
- `mailpit` (port 8025): Email testing
- `celeryworker`: Background tasks
- `celerybeat`: Scheduled tasks
- `flower` (port 5555): Celery monitoring

### Environment Variables
Located in `.envs/.local/`:
- `.django`: Django settings (SECRET_KEY, DEBUG, DEEPSEEK_API_KEY, etc.)
- `.postgres`: Database credentials

### Testing
```bash
# Run all tests
docker compose -f docker-compose.local.yml run --rm django pytest

# Run with coverage
docker compose -f docker-compose.local.yml run --rm django pytest --cov

# Run specific test
docker compose -f docker-compose.local.yml run --rm django pytest plataforma_de_servicos/produto/tests/test_models.py
```

### Code Quality Tools
```bash
# Ruff linting
ruff check .

# Ruff formatting
ruff format .

# Type checking
mypy plataforma_de_servicos

# Template linting
djlint plataforma_de_servicos/templates
```

## Important Patterns & Conventions

1. **TimeStampedModel Usage:**
   - Inherit from `core.models.TimeStampedModel` for auto timestamps
   - Provides `created` and `modified` fields

2. **AutoSlugField:**
   - Used in Categoria, Produto, Atributo, Inventario
   - Auto-generates slugs from name fields
   - Ensures URL-friendly identifiers

3. **Atomic Transactions:**
   - Stock movements use `@transaction.atomic`
   - Database has `ATOMIC_REQUESTS = True`
   - Critical for inventory consistency

4. **Admin Inlines:**
   - Use `autocomplete_fields` for foreign keys with many options
   - Requires model registration with `search_fields` defined
   - Example: VariacaoProdutoInline needs ValorAtributo registered

5. **REST API Endpoints:**
   - `/api/` prefix for all API routes
   - ViewSets for produto and categoria
   - Serializers with nested relationships

6. **HTMX Integration:**
   - Views check for `HX-Request` header
   - Return partial templates for AJAX requests
   - Full page render for normal requests

## File Structure Reference

```
plataforma_de_servicos/
├── users/
│   ├── models.py          # User, Funcionario, Cliente
│   ├── admin.py           # User admin customization
│   └── forms.py           # User forms
│
├── produto/
│   ├── models.py          # Produto, Categoria, Atributo, VariacaoProduto
│   ├── admin/
│   │   ├── admin.py       # Standard admin
│   │   └── gerente_admin.py  # Gerente admin (ERROR HERE)
│   ├── serializers.py     # DRF serializers
│   └── views.py           # Product views
│
├── estoque/
│   ├── models.py          # Estoque, EstoqueItens, proxy models
│   └── admin.py           # Stock admin
│
├── inventario/
│   ├── models.py          # Inventario, InventarioSaldo
│   └── admin.py           # Inventory admin
│
├── cart/
│   ├── cart.py            # Cart class (session-based)
│   └── views.py           # Cart AJAX views
│
├── core/
│   ├── models.py          # TimeStampedModel
│   └── admin.py           # GerenteAdminSite definition
│
└── templates/
    └── pages/             # Public-facing templates
```

## Debugging Strategy

1. **Check Django System:**
   ```bash
   just manage check
   ```

2. **View Logs:**
   ```bash
   just logs django
   just logs postgres
   just logs celeryworker
   ```

3. **Database Shell:**
   ```bash
   just manage dbshell
   ```

4. **Django Shell:**
   ```bash
   just manage shell_plus
   ```

5. **Migrations:**
   ```bash
   just manage showmigrations
   just manage migrate --plan
   ```

6. **Celery Monitoring:**
   - Open Flower UI: http://localhost:5555
   - Check task status, worker health, queues

7. **Email Testing:**
   - Open Mailpit UI: http://localhost:8025
   - View all emails sent by the application

## Next Steps to Fix Current Error

1. Open `plataforma_de_servicos/produto/admin/gerente_admin.py`
2. Add `ValorAtributoAdmin` class with `search_fields`
3. Register `ValorAtributo` in gerente_site
4. Verify with `just manage check`
5. Test autocomplete functionality in admin

## Security Considerations

- LLM API keys stored in environment variables (DEEPSEEK_API_KEY)
- Custom User model with email authentication
- django-allauth handles email verification
- MFA support enabled
- Object-level permissions via django-guardian
- CSRF protection enabled
- Secure session configuration

## Performance Optimizations

- Redis caching for sessions and data
- WhiteNoise for static file serving
- django-compressor for asset optimization
- select_related/prefetch_related in querysets
- Database indexes on slug fields (unique=True)
- Celery for async task processing

---

**Last Updated:** 2026-01-17
**Django Version:** 5.1.7
**Python Version:** 3.12.3
**Current Status:** Error in admin autocomplete_fields - needs ValorAtributo registration

