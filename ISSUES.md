# Lista de Issues

## Issues Pendentes

1.  **Carrinho (`/cart/`): Erro de renderização HTMX na exclusão de item**
    -   **Descrição:** Ao excluir um item do carrinho de compras, a resposta do servidor é um JSON em vez de um componente HTML renderizado, fazendo com que o JSON bruto seja exibido na tela.
    -   **Local:** Página do carrinho (`/cart/`).
    -   **Causa provável:** Problema na renderização da resposta HTMX no backend.

2.  **Página de Produto: Preço total não atualiza com a seleção de atributo**
    -   **Descrição:** Na página de detalhes do produto, ao selecionar um atributo diferente (ex: cor, tamanho) que possui um preço associado, o preço total do produto exibido na página não é atualizado.
    -   **Local:** Página de detalhes do produto.
    -   **Causa provável:** O evento de seleção de atributo não está acionando a atualização do preço no frontend.
