# Lista de Issues

## Issues Corrigidas

1.  **Carrinho (`/cart/`): Erro de renderização HTMX na exclusão de item**
    -   **Descrição:** Ao excluir um item do carrinho de compras, a resposta do servidor é um JSON em vez de um componente HTML renderizado, fazendo com que o JSON bruto seja exibido na tela.
    -   **Status:** Corrigido na branch `v1.2.0`. A resposta JSON agora é tratada por JavaScript no frontend.

2.  **Página de Produto: Preço total não atualiza com a seleção de atributo**
    -   **Descrição:** Na página de detalhes do produto, ao selecionar um atributo diferente (ex: cor, tamanho) que possui um preço associado, o preço total do produto exibido na página não é atualizado.
    -   **Status:** Corrigido na branch `v1.2.0`. Implementado cálculo de preço dinâmico com JavaScript e um novo endpoint.

## Issues Pendentes

3.  **Integração de Pagamento com PIX (Nova Feature)**
    -   **Descrição:** Implementar um método de pagamento via PIX no checkout.
    -   **Local:** Checkout (`/payment/checkout/`).
    -   **Status:** Pendente.

    ---

    ### Guia de Implementação Sugerido

    A ideia é gerar um código "PIX Copia e Cola" e o QR Code correspondente para cada pedido. Isso é mais seguro que um QR Code estático, pois o valor e um identificador do pedido são incluídos.

    #### Passo 1: Instalar Bibliotecas
    Você precisará de duas bibliotecas: uma para gerar o payload do PIX (a string de dados) e outra para transformar essa string em um QR Code.
    ```bash
    pip install python-pix qrcode[pil]
    ```
    *Observação: Adicionar `python-pix` e `qrcode` ao arquivo `requirements/base.txt`.*

    #### Passo 2: Configurar Dados do PIX
    No seu arquivo de settings (ex: `config/settings/base.py` ou em variáveis de ambiente em `.envs/.local/.django`), adicione as informações da sua conta.
    ```python
    # config/settings/base.py
    PIX_KEY = os.environ.get("PIX_KEY", "sua-chave-pix-aqui")
    PIX_MERCHANT_NAME = os.environ.get("PIX_MERCHANT_NAME", "Nome da Sua Loja")
    PIX_MERCHANT_CITY = os.environ.get("PIX_MERCHANT_CITY", "Sua Cidade")
    ```

    #### Passo 3: Criar um Serviço para Gerar o PIX
    No app `payment`, crie uma função em `services.py` para gerar o código PIX.
    ```python
    # plataforma_de_servicos/payment/services.py
    from pix_utils.pix import Pix
    from django.conf import settings
    import qrcode
    from io import BytesIO
    import base64

    def gerar_cobranca_pix(pedido):
        """
        Gera o payload 'Copia e Cola' e o QR Code em base64 para um pedido.
        """
        pix = Pix(
            pix_key=settings.PIX_KEY,
            merchant_name=settings.PIX_MERCHANT_NAME,
            merchant_city=settings.PIX_MERCHANT_CITY,
        )
        pix.set_amount(pedido.amount_paid)
        pix.set_txid(str(pedido.id))
        pix.set_description(f"Pedido #{pedido.id} - {settings.PIX_MERCHANT_NAME}")

        payload = pix.get_br_code()
        img = qrcode.make(payload)
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return payload, qr_code_base64
    ```

    #### Passo 4: Criar uma View para Exibir o PIX
    No `checkout`, após o cliente confirmar o pedido, redirecione para uma página que mostra o QR Code.
    ```python
    # plataforma_de_servicos/payment/views.py
    from .services import gerar_cobranca_pix

    def pagamento_pix_view(request, order_id):
        pedido = get_object_or_404(Order, id=order_id)
        pix_payload, pix_qr_code = gerar_cobranca_pix(pedido)
        context = {
            "pedido": pedido,
            "pix_payload": pix_payload,
            "pix_qr_code": pix_qr_code,
        }
        return render(request, "payment/pagamento_pix.html", context)
    ```
    *Observação: Não se esqueça de adicionar a URL para esta view em `payment/urls.py`.*

    #### Passo 5: Criar o Template
    Crie um template `payment/pagamento_pix.html` para mostrar o QR Code e o código "Copia e Cola".
    ```html
    <!-- payment/pagamento_pix.html -->
    {% extends "base.html" %}

    {% block content %}
    <div class="container text-center">
        <h2>Pague com PIX para confirmar seu pedido #{{ pedido.id }}</h2>
        <p>Escaneie o QR Code abaixo com o app do seu banco.</p>
        
        <img src="data:image/png;base64,{{ pix_qr_code }}" alt="PIX QR Code" class="img-fluid mb-3" style="max-width: 300px;">
        
        <p>Ou use o código Copia e Cola:</p>
        <div class="input-group mb-3 mx-auto" style="max-width: 500px;">
            <input type="text" id="pix-payload" class="form-control" value="{{ pix_payload }}" readonly>
            <button class="btn btn-outline-secondary" type="button" onclick="copiarPix()">Copiar</button>
        </div>
        
        <p class="text-muted">Após o pagamento, seu pedido será processado.</p>
    </div>

    <script>
    function copiarPix() {
        const input = document.getElementById('pix-payload');
        input.select();
        document.execCommand('copy');
        alert('Código PIX copiado!');
    }
    </script>
    {% endblock %}
    ```

    ---
    **Nota Importante:** Com esta abordagem, a confirmação do pagamento **não é automática**. Será necessário verificar o recebimento do PIX manualmente e atualizar o status do pedido. Para automação, o próximo passo seria a integração com um gateway de pagamento que suporte webhooks (ex: Mercado Pago, PagSeguro).

4.  **Refatoração do Controle de Estoque (Bloqueio Otimista)**
    -   **Descrição:** A complexa lógica de `ReservaEstoque` foi removida em favor de uma abordagem mais simples e performática de "bloqueio otimista".
    -   **Status:** Concluído.
    -   **Implementação:**
        1.  O modelo `ReservaEstoque` e suas migrações foram removidos.
        2.  A classe `Cart` em `cart/cart.py` foi simplificada para não manipular mais as reservas.
        3.  Uma verificação de estoque foi adicionada no início da view `payment.views.checkout`. Se um item no carrinho não tiver estoque suficiente, o usuário é redirecionado de volta ao carrinho com uma mensagem de erro, antes de prosseguir com o pagamento.
        4.  Esta abordagem elimina a necessidade de tarefas de limpeza para carrinhos abandonados e simplifica a lógica de exibição de produtos.
