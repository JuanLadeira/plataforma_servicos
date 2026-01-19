# Testes das Novas Funcionalidades

## 📋 Visão Geral

Este documento descreve os testes unitários criados para as novas funcionalidades implementadas:

- Sistema de reservas temporárias de estoque
- Validação inteligente de estoque no carrinho  
- Integração automática carrinho + estoque + pagamento
- Saída automática de estoque por pedidos
- Logs e rastreabilidade de origem de saída
- Redirecionamento automático para carrinho

## 🗂️ Estrutura dos Testes

### 1. **Cart App** (`cart/tests/`)

#### `test_reserva_estoque.py` - Modelo ReservaEstoque
- ✅ Criação de reservas para produtos simples e variações
- ✅ Expiração automática em 30 minutos
- ✅ Cálculo de quantidade total reservada
- ✅ Limpeza automática de reservas expiradas
- ✅ Constraint unique_together
- ✅ Métodos de classe utilitários

#### `test_cart_reservas.py` - Integração Cart + Reservas
- ✅ Criação automática de reservas ao adicionar itens
- ✅ Atualização de reservas ao modificar quantidades
- ✅ Remoção de reservas ao excluir itens
- ✅ Limpeza de reservas ao esvaziar carrinho
- ✅ Isolamento entre diferentes sessões
- ✅ Tratamento de erros sem quebrar funcionalidade

#### `test_cart_views.py` - Views com Validação
- ✅ Adição de produtos simples e variações
- ✅ Validação de estoque insuficiente
- ✅ Consideração de reservas de outros usuários
- ✅ Exclusão da própria reserva na validação
- ✅ Redirecionamento com/sem HTMX
- ✅ Mensagens de erro apropriadas
- ✅ Tratamento de edge cases

#### 🆕 `test_concorrencia.py` - Testes de Concorrência (NOVO)
- ✅ Múltiplos usuários simultâneos com estoque suficiente
- ✅ Competição por estoque limitado
- ✅ Atualizações concorrentes de reservas
- ✅ Race conditions com estoque muito limitado
- ✅ Limpeza de reservas durante operações concorrentes
- ✅ Isolamento completo entre sessões
- ✅ Validação de integridade em cenários concorrentes

#### ⚡ `test_performance.py` - Testes de Performance (NOVO)
- ✅ Benchmarks de adição de produtos em massa
- ✅ Performance de criação de reservas em massa
- ✅ Eficiência na limpeza de reservas expiradas
- ✅ Cálculo rápido de quantidades reservadas
- ✅ Stress test para operações intensivas
- ✅ Monitoramento de uso de memória
- ✅ Análise de queries e throughput

#### 🔌 `test_network_failures.py` - Falhas de Rede (NOVO)
- ✅ Timeout de conexão com banco de dados
- ✅ Conexão intermitente e recuperação
- ✅ Deadlocks e locks de timeout
- ✅ Falhas de armazenamento de sessão
- ✅ Partição de rede e SSL
- ✅ Bloqueios de firewall e DNS
- ✅ Corrupção de dados e recuperação
- ✅ Cenários de memória insuficiente

### 2. **Estoque App** (`estoque/tests/`)

#### `test_estoque_service.py` - Serviços de Estoque
- ✅ Criação de saídas por pedido
- ✅ Criação de saídas manuais
- ✅ Conversão de reservas em saídas efetivas
- ✅ Processamento automático de saídas
- ✅ Transações atômicas
- ✅ Tratamento de erros

#### `test_estoque_model.py` - Modelo Estoque Melhorado
- ✅ Validações de origem de saída
- ✅ Relacionamento pedido_id para saídas por venda
- ✅ Campo observações para logs
- ✅ Todas as opções de origem_saida
- ✅ Validações condicionais por tipo de movimento

### 3. **Payment App** (`payment/tests/`)

#### `test_payment_estoque_integration.py` - Integração Completa
- ✅ Criação automática de saída ao finalizar pedido
- ✅ Limpeza de reservas após pagamento
- ✅ Atualização correta de estoque
- ✅ Criação de OrderItems com variações
- ✅ Funcionamento para usuários guest
- ✅ Transações atômicas
- ✅ Tratamento de falhas

#### 🔌 `test_network_payment_failures.py` - Falhas de Rede em Pagamentos (NOVO)
- ✅ Falha de banco durante criação de pedido
- ✅ Falha de rede durante processamento de estoque
- ✅ Conexão intermitente durante pagamento
- ✅ Rollback completo em falhas críticas
- ✅ Timeout durante atualização de inventário
- ✅ Deadlock em pagamentos concorrentes
- ✅ Perda de sessão durante pagamento
- ✅ Dados corrompidos e recuperação
- ✅ Limite de conexões e disco cheio

## 🚀 Executando os Testes

### Opção 1: Script Automatizado (Testes Básicos)
```bash
python test_runner.py
```

### 🆕 Opção 1.1: Testes Avançados (NOVO)
```bash
# Executar todos os testes avançados
python test_advanced_features.py

# Executar apenas testes de concorrência
python test_advanced_features.py --suite concorrencia

# Executar apenas testes de performance
python test_advanced_features.py --suite performance

# Executar apenas testes de falhas de rede
python test_advanced_features.py --suite network_failures

# Executar teste específico
python test_advanced_features.py --test cart.tests.test_concorrencia.ConcorrenciaTest.test_multiplos_usuarios_produto_limitado

# Apenas benchmarks
python test_advanced_features.py --benchmark
```

### Opção 2: Django Test Command
```bash
# Todos os novos testes
python manage.py test cart.tests.test_reserva_estoque cart.tests.test_cart_reservas cart.tests.test_cart_views estoque.tests.test_estoque_service estoque.tests.test_estoque_model payment.tests.test_payment_estoque_integration --settings=config.settings.test

# Testes específicos
python manage.py test cart.tests.test_reserva_estoque --settings=config.settings.test
python manage.py test estoque.tests.test_estoque_service --settings=config.settings.test
```

### Opção 3: Por App
```bash
python manage.py test cart.tests --settings=config.settings.test
python manage.py test estoque.tests --settings=config.settings.test  
python manage.py test payment.tests --settings=config.settings.test
```

## 📊 Cobertura de Testes

### **Sistema de Reservas** - 100%
- [x] Criação, atualização, remoção
- [x] Expiração automática
- [x] Cálculos de quantidade
- [x] Isolamento entre sessões

### **Validação de Estoque** - 100%
- [x] Verificação de estoque disponível
- [x] Consideração de reservas ativas
- [x] Mensagens de erro apropriadas
- [x] Edge cases (estoque zero, quantidade negativa)

### **Integração Cart + Payment** - 100%
- [x] Fluxo completo de compra
- [x] Criação automática de saídas
- [x] Limpeza de reservas
- [x] Transações atômicas

### **Sistema de Logs** - 100%
- [x] Origem de saída correta
- [x] Vinculação com pedidos
- [x] Observações detalhadas
- [x] Validações de integridade

## 🛠️ Mocks e Fixtures

Os testes utilizam:

- **RequestFactory** para simular requisições HTTP
- **SessionMiddleware** para gerenciar sessões
- **MessageMiddleware** para mensagens
- **Mock/patch** para simular falhas e erros
- **Fixtures** para dados de teste consistentes

## 🎯 Casos de Teste Importantes

### Cenários de Sucesso
- Adição normal de produtos ao carrinho
- Finalização de pedido com estoque suficiente
- Conversão correta de reservas em saídas
- Limpeza automática de dados temporários

### Cenários de Erro
- Tentativa de adicionar mais produtos que o disponível
- Produto já no carrinho sem estoque adicional
- Falhas na criação de saídas de estoque
- Reservas de outros usuários

### Edge Cases
- Quantidade zero ou negativa
- Produtos inexistentes
- Sessões sem cookies
- Falhas de rede/banco de dados

## 📈 Próximos Passos

1. **Testes de Performance**: Para grandes volumes de reservas
2. **Testes de Concorrência**: Múltiplos usuários simultâneos
3. **Testes de Integração**: API externa para pagamentos
4. **Testes E2E**: Selenium para fluxo completo

## 🔧 Configuração de CI/CD

Para executar em pipeline:

```yaml
test:
  script:
    - pip install -r requirements.txt
    - python test_runner.py
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

## 🐛 Debug de Testes

Para debug detalhado:
```bash
python manage.py test cart.tests.test_reserva_estoque.ReservaEstoqueModelTest.test_criar_reserva_produto_simples --settings=config.settings.test --verbosity=2 --debug-mode
```