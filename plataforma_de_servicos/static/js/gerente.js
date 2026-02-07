// All styling has been moved to gerente.css
// This file contains JavaScript functionalities for the manager interface.

document.addEventListener('DOMContentLoaded', function() {
    /**
     * Atualiza os links de popup "+" para passar o parâmetro _categoria
     * quando estiver editando um Produto. Isso permite que a criação de
     * novos Atributos e ValorAtributos já venha com a categoria preenchida.
     */
    function updateAddPopupLinks() {
        // Encontra o campo de categoria do produto (pode ser select ou hidden input)
        var categoriaField = document.querySelector('#id_categoria');
        if (!categoriaField) return;

        var categoriaId = categoriaField.value;
        if (!categoriaId) return;

        // Encontra todos os links de adicionar ValorAtributo e Atributo
        var addLinks = document.querySelectorAll('a[href*="valoratributo/add/"], a[href*="atributo/add/"]');

        addLinks.forEach(function(link) {
            var href = link.getAttribute('href');
            if (!href) return;

            // Remove parâmetro _categoria existente se houver
            var url = new URL(href, window.location.origin);
            url.searchParams.delete('_categoria');

            // Adiciona o novo parâmetro _categoria
            url.searchParams.set('_categoria', categoriaId);

            link.setAttribute('href', url.pathname + url.search);
        });
    }

    // Executa na carga inicial
    updateAddPopupLinks();

    // Observa mudanças no campo categoria
    var categoriaField = document.querySelector('#id_categoria');
    if (categoriaField) {
        categoriaField.addEventListener('change', updateAddPopupLinks);
    }

    // Observa mudanças no DOM para quando novos inlines forem adicionados
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                updateAddPopupLinks();
            }
        });
    });

    // Observa a área de inlines
    var inlinesContainer = document.querySelector('.inline-group, .inline-related');
    if (inlinesContainer) {
        observer.observe(inlinesContainer, { childList: true, subtree: true });
    }

    // Também observa o body para Select2 dropdowns que são adicionados dinamicamente
    observer.observe(document.body, { childList: true, subtree: true });
});
