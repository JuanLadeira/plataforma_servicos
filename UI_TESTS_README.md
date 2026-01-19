# Testes de Interface de Usuário (UI) - Selenium

Este documento descreve como executar e manter os testes de UI automatizados para o sistema de carrinho de compras.

## 📋 Visão Geral

Os testes de UI verificam o comportamento da interface do usuário, especialmente:

- ✅ Adição de produtos ao carrinho na listagem
- ✅ Adição de produtos ao carrinho na página de detalhes
- ✅ Atualização de quantidades no carrinho
- ✅ Remoção de produtos do carrinho
- ✅ Redirecionamentos após ações HTMX
- ✅ Validação de estoque
- ✅ Feedback visual (botões, mensagens)

## 🚀 Como Executar

### Método 1: Script Direto (Recomendado)
```bash
# Executar todos os testes UI
python run_ui_tests.py

# Executar sem interface gráfica (padrão)
python run_ui_tests.py --headless

# Executar com interface gráfica (para debug)
python run_ui_tests.py --no-headless

# Executar teste específico
python run_ui_tests.py --test-pattern "test_add_product"
```

### Método 2: Taskipy
```bash
# Executar testes UI via taskipy
task test-ui
```

### Método 3: Pytest Direto
```bash
# Executar testes UI diretamente
pytest plataforma_de_servicos/cart/tests/test_ui_selenium.py -v -s
```

### Método 4: Docker (CI/CD)
```bash
# Executar testes UI no container
docker compose -f docker-compose.local.yml run --rm django \
    pytest plataforma_de_servicos/cart/tests/test_ui_selenium.py -v
```

## 🛠️ Configuração

### Dependências
```bash
# Instalar dependências (já incluído no pyproject.toml)
pip install selenium>=4.15.0 webdriver-manager>=4.0.0
```

### ChromeDriver
O `webdriver-manager` baixa automaticamente o ChromeDriver compatível. Não é necessário instalação manual.

### Variáveis de Ambiente
- `SELENIUM_HEADLESS=true` - Executa em modo headless (padrão)
- `SELENIUM_HEADLESS=false` - Executa com interface gráfica

## 📝 Estrutura dos Testes

```
plataforma_de_servicos/cart/tests/test_ui_selenium.py
├── CartUITestCase (classe base)
├── AddToCartFromListingTest
│   ├── test_add_product_to_cart_from_home_page
│   └── test_add_product_with_quantity_validation
├── CartUpdateTest
│   ├── test_update_product_quantity_in_cart
│   └── test_remove_product_from_cart
└── CartNavigationTest
    ├── test_product_detail_add_to_cart
    └── test_continue_shopping_button
```

## 🔍 Testes Implementados

### 1. Adição ao Carrinho da Listagem
**Teste:** `test_add_product_to_cart_from_home_page`
- Navega para página inicial
- Clica no botão "Adicionar ao carrinho"
- Verifica redirecionamento para carrinho
- Confirma que produto aparece no carrinho

### 2. Validação de Estoque
**Teste:** `test_add_product_with_quantity_validation`
- Testa adição múltipla de produtos
- Verifica limites de estoque
- Confirma comportamento com produtos de estoque baixo

### 3. Atualização de Quantidade
**Teste:** `test_update_product_quantity_in_cart`
- Adiciona produto ao carrinho
- Altera quantidade no carrinho
- Clica em atualizar
- Verifica se total foi recalculado

### 4. Remoção de Produto
**Teste:** `test_remove_product_from_cart`
- Adiciona produto ao carrinho
- Remove produto do carrinho
- Verifica se item foi removido
- Confirma carrinho vazio

### 5. Adição na Página de Detalhes
**Teste:** `test_product_detail_add_to_cart`
- Navega para página de detalhes
- Clica em adicionar ao carrinho
- Verifica feedback visual ("Adicionado!")
- Confirma redirecionamento

### 6. Navegação do Carrinho
**Teste:** `test_continue_shopping_button`
- Testa botão "Continuar Comprando"
- Verifica retorno à página inicial

## 🐛 Debugging

### Executar com Interface Gráfica
```bash
python run_ui_tests.py --no-headless
```

### Debug de Teste Específico
```bash
python run_ui_tests.py --test-pattern "test_add_product" --no-headless
```

### Logs Detalhados
```bash
pytest plataforma_de_servicos/cart/tests/test_ui_selenium.py::AddToCartFromListingTest::test_add_product_to_cart_from_home_page -v -s --tb=long
```

## 🔧 Configurações Avançadas

### Timeout Personalizado
Edite as configurações na classe `CartUITestCase`:
```python
self.selenium.implicitly_wait(10)  # 10 segundos padrão
```

### Screenshots em Falhas
Adicione este método à classe de teste:
```python
def tearDown(self):
    if hasattr(self._outcome, 'errors') and self._outcome.errors:
        # Capturar screenshot em caso de erro
        screenshot_name = f"error_{self._testMethodName}.png"
        self.selenium.save_screenshot(screenshot_name)
```

### Outros Navegadores
Para usar Firefox, substitua na configuração:
```python
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager

firefox_options = FirefoxOptions()
if os.environ.get('SELENIUM_HEADLESS', 'true').lower() == 'true':
    firefox_options.add_argument('--headless')

service = Service(GeckoDriverManager().install())
cls.selenium = webdriver.Firefox(service=service, options=firefox_options)
```

## 🎯 Boas Práticas

### 1. Aguardar Elementos
Sempre use `WebDriverWait` ao invés de `time.sleep()`:
```python
element = WebDriverWait(self.selenium, 10).until(
    EC.presence_of_element_located((By.ID, 'my-element'))
)
```

### 2. Seletores Robustos
Prefira seletores que não mudam:
```python
# ✅ Bom - usando ID único
By.ID, 'cart-item-123'

# ✅ Bom - usando atributo específico  
By.CSS_SELECTOR, 'button[hx-vals*="product_id"]'

# ❌ Evitar - seletores genéricos
By.CLASS_NAME, 'btn'
```

### 3. Dados de Teste
Use factories para criar dados consistentes:
```python
self.produto = ProdutoFactory(
    produto="Pizza Test",
    preco="25.90",
    estoque=10,
)
```

### 4. Limpeza
Sempre limpe o estado entre testes:
```python
def setUp(self):
    # Limpar carrinho, logout, etc.
    pass
```

## 🚨 Solução de Problemas

### ChromeDriver não encontrado
```bash
# O webdriver-manager resolve automaticamente, mas se houver problemas:
pip install --upgrade webdriver-manager
```

### Testes falhando por timeout
- Aumente o timeout em `wait_for_element()`
- Verifique se o servidor está rodando
- Confirme se os elementos HTMX estão carregando

### Elementos não encontrados
- Use `--no-headless` para ver o que está acontecendo
- Verifique se os seletores CSS estão corretos
- Confirme se os dados de teste foram criados

### Performance
- Use `--reuse-db` para reutilizar banco de dados
- Configure `TransactionTestCase` se necessário para transações

## 📈 Métricas e Relatórios

### Cobertura de Testes
```bash
pytest plataforma_de_servicos/cart/tests/test_ui_selenium.py --cov=plataforma_de_servicos.cart --cov-report=html
```

### Relatório JUnit (para CI)
```bash
pytest plataforma_de_servicos/cart/tests/test_ui_selenium.py --junit-xml=ui_tests_report.xml
```

### Tempo de Execução
```bash
pytest plataforma_de_servicos/cart/tests/test_ui_selenium.py --durations=10
```

## 🔄 Integração Contínua

### GitHub Actions Example
```yaml
- name: Run UI Tests
  run: |
    python run_ui_tests.py --headless
  env:
    SELENIUM_HEADLESS: true
```

### Docker para CI
```dockerfile
# Adicionar ao Dockerfile para CI
RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-chromedriver
```

---

**Nota:** Os testes de UI são mais lentos que testes unitários. Execute-os em momentos estratégicos como antes de deploys ou em pipelines de CI/CD.