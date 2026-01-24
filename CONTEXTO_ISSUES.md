# Plano de Trabalho e Issues

## Backlog

### Feature: Mudar fluxo de compra para Geração de Leads

*Descrição: Transformar o carrinho de compras em uma ferramenta de captação de leads. O cliente demonstrará interesse nos produtos, e os corretores serão notificados para iniciar o atendimento.*

---

**História 1: Criação do Modelo `Corretor`**
-   **Status:** A Fazer
-   **Descrição:** Criar uma forma de cadastrar e gerenciar os corretores (ou vendedores) no sistema.
-   **Tarefas:**
    1.  Criar um novo app Django: `corretores`.
    2.  Definir o modelo `Corretor` em `models.py` (com `nome`, `email`, `telefone`, `user`).
    3.  Registrar o modelo no `admin.py`.
    4.  Gerar e aplicar as migrações.

**História 2: Transformar o Checkout em "Demonstração de Interesse"**
-   **Status:** A Fazer
-   **Descrição:** Substituir o fluxo de pagamento por um formulário de "interesse" para ser contatado.
-   **Tarefas:**
    1.  Alterar o template do carrinho.
    2.  Criar a view, form e template para o formulário de interesse.
    3.  Criar o modelo `InteresseCompra` para armazenar os dados do lead.

**História 3: Sistema de Notificação para Corretores**
-   **Status:** A Fazer
-   **Descrição:** Notificar todos os corretores por e-mail quando um novo interesse for registrado.
-   **Tarefas:**
    1.  Criar um serviço de envio de e-mail.
    2.  Integrar o serviço ao final da "demonstração de interesse".
    3.  O e-mail deve conter os detalhes do cliente e dos produtos.

---

### Outras Issues Pendentes

**1. Integração de Pagamento com PIX (Nova Feature)**
-   **Descrição:** Implementar um método de pagamento via PIX no checkout.
-   **Local:** Checkout (`/payment/checkout/`).
-   **Status:** Pendente (Prioridade Baixa).

<details>
<summary>Guia de Implementação Sugerido para PIX</summary>

A ideia é gerar um código "PIX Copia e Cola" e o QR Code correspondente para cada pedido.

**Passo 1: Instalar Bibliotecas**
```bash
pip install python-pix qrcode[pil]
```
*Observação: Adicionar `python-pix` e `qrcode` ao arquivo `requirements/base.txt`.*

**Passo 2: Configurar Dados do PIX**
```python
# config/settings/base.py
PIX_KEY = os.environ.get("PIX_KEY", "sua-chave-pix-aqui")
PIX_MERCHANT_NAME = os.environ.get("PIX_MERCHANT_NAME", "Nome da Sua Loja")
PIX_MERCHANT_CITY = os.environ.get("PIX_MERCHANT_CITY", "Sua Cidade")
```

**Passo 3: Criar um Serviço para Gerar o PIX**
```python
# plataforma_de_servicos/payment/services.py
from pix_utils.pix import Pix
from django.conf import settings
import qrcode
from io import BytesIO
import base64

def gerar_cobranca_pix(pedido):
    pix = Pix(...)
    # ... implementação ...
    return payload, qr_code_base64
```

**Passo 4: Criar uma View para Exibir o PIX**
```python
# plataforma_de_servicos/payment/views.py
from .services import gerar_cobranca_pix

def pagamento_pix_view(request, order_id):
    # ... implementação ...
    return render(request, "payment/pagamento_pix.html", context)
```

**Passo 5: Criar o Template**
```html
<!-- payment/pagamento_pix.html -->
{% extends "base.html" %}
{% block content %}
    <!-- ... implementação ... -->
{% endblock %}
```

</details>

---

## Issues Concluídas

-   **Refatoração do Controle de Estoque (Bloqueio Otimista)**
-   **Carrinho (`/cart/`): Erro de renderização HTMX na exclusão de item**
-   **Página de Produto: Preço total não atualiza com a seleção de atributo**