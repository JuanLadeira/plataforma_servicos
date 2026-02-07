/**
 * Widget de seleção de valores de atributo
 * Gerencia o estado visual dos chips quando selecionados/deselecionados
 * Usa checkboxes mas simula radio buttons para atributos de seleção única
 */
(function() {
    'use strict';

    function initValoresAtributoWidget() {
        // Encontra todos os containers do widget
        const containers = document.querySelectorAll('.valores-atributo-container');

        containers.forEach(container => {
            // Se já foi inicializado, pula
            if (container.dataset.initialized) return;
            container.dataset.initialized = 'true';

            // Adiciona listener para cada checkbox
            const inputs = container.querySelectorAll('.valor-checkbox');
            inputs.forEach(input => {
                // Atualiza estado inicial
                updateChipState(input);

                // Listener para mudanças
                input.addEventListener('change', function() {
                    handleInputChange(this, container);
                });
            });
        });
    }

    function handleInputChange(input, container) {
        const isSingleSelection = input.dataset.multipla === 'false';
        const atributo = input.dataset.atributo;

        // Para seleção única, desmarcar outros chips do mesmo atributo
        if (isSingleSelection && atributo && input.checked) {
            const sameGroupInputs = container.querySelectorAll(
                `input[data-atributo="${CSS.escape(atributo)}"]`
            );
            sameGroupInputs.forEach(otherInput => {
                if (otherInput !== input && otherInput.checked) {
                    otherInput.checked = false;
                    updateChipState(otherInput);
                }
            });
        }

        updateChipState(input);
    }

    function updateChipState(input) {
        const chip = input.closest('.valor-chip');
        if (!chip) return;

        if (input.checked) {
            chip.classList.add('checked');
        } else {
            chip.classList.remove('checked');
        }
    }

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initValoresAtributoWidget);
    } else {
        initValoresAtributoWidget();
    }

    // Re-inicializa quando novos inlines são adicionados (Django inline formsets)
    const observer = new MutationObserver(function(mutations) {
        let shouldInit = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 &&
                        (node.classList?.contains('valores-atributo-container') ||
                         node.querySelector?.('.valores-atributo-container'))) {
                        shouldInit = true;
                    }
                });
            }
        });
        if (shouldInit) {
            initValoresAtributoWidget();
        }
    });

    // Observa mudanças no body para detectar novos inlines
    observer.observe(document.body, { childList: true, subtree: true });

    // Expõe função globalmente para reinicialização manual se necessário
    window.initValoresAtributoWidget = initValoresAtributoWidget;
})();
