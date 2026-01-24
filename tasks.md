# Task: Identificar Testes com Timeout por Marker

## Contexto
Precisamos identificar quais markers/domínios de teste estão causando timeouts para atuar na área correta.

## Configuração Atual (pyproject.toml)
- **Timeout por teste:** 15 segundos
- **Método de timeout:** thread
- **Comando base:** `docker compose -f docker-compose.local.yml run --rm django pytest -vv -s`

## Markers Disponíveis
| # | Marker | Descrição | Status | Resultado |
|---|--------|-----------|--------|-----------|
| 1 | `produto` | Testes do app de produto | PENDENTE | - |
| 2 | `cart` | Testes do carrinho de compras | PENDENTE | - |
| 3 | `estoque` | Testes do app de estoque | PENDENTE | - |
| 4 | `payment` | Testes do app de pagamento | PENDENTE | - |
| 5 | `users` | Testes do app de usuários | PENDENTE | - |
| 6 | `empresa` | Testes do app de empresa | PENDENTE | - |
| 7 | `servico` | Testes do app de serviço | PENDENTE | - |
| 8 | `inventario` | Testes do app de inventário | PENDENTE | - |
| 9 | `account` | Testes do app de account | PENDENTE | - |
| 10 | `slow` | Testes lentos (performance, UI) | PENDENTE | - |
| 11 | `integration` | Testes de integração | PENDENTE | - |
| 12 | `ui` | Testes de interface Selenium | PENDENTE | - |

## Comandos para Execução

### Comando padrão por marker:
```bash
docker compose -f docker-compose.local.yml run --rm django pytest -m <MARKER> -vv -s --tb=short 2>&1 | tee test_<MARKER>.log
```

### Comandos específicos:
```bash
# 1. Produto
docker compose -f docker-compose.local.yml run --rm django pytest -m produto -vv -s --tb=short

# 2. Cart
docker compose -f docker-compose.local.yml run --rm django pytest -m cart -vv -s --tb=short

# 3. Estoque
docker compose -f docker-compose.local.yml run --rm django pytest -m estoque -vv -s --tb=short

# 4. Payment
docker compose -f docker-compose.local.yml run --rm django pytest -m payment -vv -s --tb=short

# 5. Users
docker compose -f docker-compose.local.yml run --rm django pytest -m users -vv -s --tb=short

# 6. Empresa
docker compose -f docker-compose.local.yml run --rm django pytest -m empresa -vv -s --tb=short

# 7. Servico
docker compose -f docker-compose.local.yml run --rm django pytest -m servico -vv -s --tb=short

# 8. Inventario
docker compose -f docker-compose.local.yml run --rm django pytest -m inventario -vv -s --tb=short

# 9. Account
docker compose -f docker-compose.local.yml run --rm django pytest -m account -vv -s --tb=short

# 10. Slow (excluir para evitar falsos positivos)
docker compose -f docker-compose.local.yml run --rm django pytest -m slow -vv -s --tb=short

# 11. Integration
docker compose -f docker-compose.local.yml run --rm django pytest -m integration -vv -s --tb=short

# 12. UI (requer Selenium/Chrome)
docker compose -f docker-compose.local.yml run --rm django pytest -m ui -vv -s --tb=short
```

## Plano de Execução

### Fase 1: Executar markers principais (apps com testes ativos)
1. [ ] `produto` - 4 arquivos de teste
2. [ ] `cart` - 11 arquivos de teste
3. [ ] `estoque` - 4 arquivos de teste
4. [ ] `payment` - 3 arquivos de teste
5. [ ] `users` - 7 arquivos de teste

### Fase 2: Executar markers secundários (apps sem testes ou vazios)
6. [ ] `empresa` - placeholder
7. [ ] `servico` - placeholder
8. [ ] `inventario` - placeholder
9. [ ] `account` - placeholder

### Fase 3: Executar markers especiais
10. [ ] `integration` - testes de integração entre apps
11. [ ] `slow` - testes marcados como lentos (espera-se timeout)
12. [ ] `ui` - testes Selenium (requer ambiente específico)

## Resultados

### Testes com Timeout Identificados
| Marker | Arquivo | Teste | Tempo |
|--------|---------|-------|-------|
| - | - | - | - |

### Testes Passando
| Marker | Total | Passou | Falhou | Timeout |
|--------|-------|--------|--------|---------|
| - | - | - | - | - |

## Ações Corretivas Necessárias
1. [ ] Identificar causa raiz dos timeouts
2. [ ] Avaliar se timeout de 15s é adequado
3. [ ] Corrigir ou marcar testes problemáticos com `@pytest.mark.slow`

## Progresso Atual
- **Fase atual:** Fase 1 - Não iniciada
- **Último marker testado:** Nenhum
- **Próximo passo:** Executar pytest -m produto

## Notas
- Testes marcados com `slow` são esperados para demorar mais
- Testes `ui` requerem Selenium e Chrome configurados
- Alguns arquivos de teste estão comentados (concorrência, performance, network_failures, ui_selenium)

---
**Última atualização:** 2026-01-18
**Branch:** v1.2.0
