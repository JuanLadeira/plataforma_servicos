/**
 * Widget para preview de saldo em tempo real no estoque
 * Calcula e exibe o saldo após a operação de entrada/saída
 */
(function() {
    'use strict';

    // Detecta se é entrada ou saída baseado na URL
    function getMovimentoTipo() {
        const path = window.location.pathname;
        if (path.includes('estoqueentrada')) return 'entrada';
        if (path.includes('estoquesaida')) return 'saida';
        if (path.includes('transferencia')) return 'transferencia';
        return null;
    }

    function initEstoqueItensWidget() {
        const movimentoTipo = getMovimentoTipo();
        if (!movimentoTipo) return;

        // Encontra todas as linhas de inline
        const inlineRows = document.querySelectorAll('.inline-related:not(.empty-form)');

        inlineRows.forEach(row => {
            initRowPreview(row, movimentoTipo);
        });

        // Observer para novas linhas adicionadas dinamicamente
        const observer = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1 && node.classList?.contains('inline-related')) {
                        initRowPreview(node, movimentoTipo);
                    }
                });
            });
        });

        const inlineGroup = document.querySelector('.inline-group');
        if (inlineGroup) {
            observer.observe(inlineGroup, { childList: true, subtree: true });
        }
    }

    function initRowPreview(row, movimentoTipo) {
        if (row.dataset.previewInitialized) return;
        row.dataset.previewInitialized = 'true';

        const quantidadeInput = row.querySelector('input[name$="-quantidade"]');
        const variacaoSelect = row.querySelector('select[name$="-variacao"]');

        if (!quantidadeInput) return;

        // Atualiza preview quando quantidade muda
        quantidadeInput.addEventListener('input', () => {
            updatePreview(row, movimentoTipo);
        });

        // Atualiza preview quando variação muda (Select2)
        if (variacaoSelect) {
            // Select2 dispara evento 'change'
            $(variacaoSelect).on('change', () => {
                updateSaldoAtual(row, variacaoSelect);
                updatePreview(row, movimentoTipo);
            });
        }
    }

    function updateSaldoAtual(row, variacaoSelect) {
        // Extrai o estoque atual do texto da opção selecionada
        // Formato: "Produto - Valor1, Valor2 [est: X]"
        const selectedText = variacaoSelect.options[variacaoSelect.selectedIndex]?.text || '';
        const match = selectedText.match(/\[est:\s*(\d+)\]/);

        const saldoAtualCell = row.querySelector('.field-saldo_atual .readonly, .field-saldo_atual p');
        if (saldoAtualCell && match) {
            saldoAtualCell.textContent = match[1];
            saldoAtualCell.dataset.saldoAtual = match[1];
        }
    }

    function updatePreview(row, movimentoTipo) {
        const quantidadeInput = row.querySelector('input[name$="-quantidade"]');
        const saldoAtualCell = row.querySelector('.field-saldo_atual .readonly, .field-saldo_atual p');
        const saldoPreviewCell = row.querySelector('.field-saldo_preview .readonly, .field-saldo_preview p');

        if (!quantidadeInput || !saldoPreviewCell) return;

        const quantidade = parseInt(quantidadeInput.value) || 0;
        let saldoAtual = 0;

        // Tenta pegar o saldo atual
        if (saldoAtualCell) {
            saldoAtual = parseInt(saldoAtualCell.dataset?.saldoAtual || saldoAtualCell.textContent) || 0;
        }

        let saldoNovo;
        if (movimentoTipo === 'entrada') {
            saldoNovo = saldoAtual + quantidade;
        } else if (movimentoTipo === 'saida' || movimentoTipo === 'transferencia') {
            saldoNovo = saldoAtual - quantidade;
        } else {
            return;
        }

        // Atualiza a célula de preview
        if (quantidade > 0) {
            saldoPreviewCell.textContent = saldoNovo;

            // Aplica classes de estilo
            saldoPreviewCell.classList.remove('saldo-preview-positive', 'saldo-preview-negative');
            if (movimentoTipo === 'entrada') {
                saldoPreviewCell.classList.add('saldo-preview-positive');
            } else if (saldoNovo < 0) {
                saldoPreviewCell.classList.add('saldo-preview-negative');
            } else {
                saldoPreviewCell.classList.add('saldo-preview-positive');
            }
        } else {
            saldoPreviewCell.textContent = '-';
            saldoPreviewCell.classList.remove('saldo-preview-positive', 'saldo-preview-negative');
        }
    }

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEstoqueItensWidget);
    } else {
        initEstoqueItensWidget();
    }

    // Re-inicializa após Select2 inicializar (pode demorar)
    setTimeout(initEstoqueItensWidget, 500);
})();
