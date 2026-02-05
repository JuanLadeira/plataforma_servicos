# Lista de Issues

## Issues Corrigidas

1.  **Carrinho (`/cart/`): Erro de renderização HTMX na exclusão de item**
    -   **Descrição:** Ao excluir um item do carrinho de compras, a resposta do servidor é um JSON em vez de um componente HTML renderizado, fazendo com que o JSON bruto seja exibido na tela.
    -   **Status:** Corrigido na branch `v1.2.0`. A resposta JSON agora é tratada por JavaScript no frontend.

2.  **Página de Produto: Preço total não atualiza com a seleção de atributo**
    -   **Descrição:** Na página de detalhes do produto, ao selecionar um atributo diferente (ex: cor, tamanho) que possui um preço associado, o preço total do produto exibido na página não é atualizado.
    -   **Status:** Corrigido na branch `v1.2.0`. Implementado cálculo de preço dinâmico com JavaScript e um novo endpoint.

4.  **Refatoração do Controle de Estoque (Bloqueio Otimista)**
    -   **Descrição:** A complexa lógica de `ReservaEstoque` foi removida em favor de uma abordagem mais simples e performática de "bloqueio otimista".
    -   **Status:** Concluído.
    -   **Implementação:**
        1.  O modelo `ReservaEstoque` e suas migrações foram removidos.
        2.  A classe `Cart` em `cart/cart.py` foi simplificada para não manipular mais as reservas.
        3.  Uma verificação de estoque foi adicionada no início da view `payment.views.checkout`. Se um item no carrinho não tiver estoque suficiente, o usuário é redirecionado de volta ao carrinho com uma mensagem de erro, antes de prosseguir com o pagamento.
        4.  Esta abordagem elimina a necessidade de tarefas de limpeza para carrinhos abandonados e simplifica a lógica de exibição de produtos.
