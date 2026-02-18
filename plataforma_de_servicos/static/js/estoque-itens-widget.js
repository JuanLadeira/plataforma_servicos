/**
 * Widget para preview de saldo em tempo real no estoque
 * Usa polling para detectar mudanças no select2 + API para buscar saldo
 */
(function() {
    'use strict';

    const estoqueCache = {};
    let initialized = false;

    function getMovimentoTipo() {
        const path = window.location.pathname;
        if (path.includes('estoqueentrada')) return 'entrada';
        if (path.includes('estoquesaida')) return 'saida';
        if (path.includes('transferencia')) return 'transferencia';
        return null;
    }

    function init() {
        const tipo = getMovimentoTipo();
        if (!tipo) return;
        if (initialized) return;
        initialized = true;

        console.log('[EstoqueWidget] Iniciando para:', tipo);

        // Processa linhas existentes
        processRows(tipo);

        // Observer para novas linhas
        const inlineGroup = document.querySelector('.inline-group');
        if (inlineGroup) {
            new MutationObserver(() => {
                setTimeout(() => processRows(tipo), 300);
            }).observe(inlineGroup, { childList: true, subtree: true });
        }
    }

    function processRows(tipo) {
        document.querySelectorAll('.inline-group tr.form-row:not(.empty-form)').forEach(row => {
            setupRow(row, tipo);
        });
    }

    function setupRow(row, tipo) {
        const variacaoSelect = row.querySelector('select[name$="-variacao"]');
        const quantidadeInput = row.querySelector('input[name$="-quantidade"]');

        if (!variacaoSelect || !quantidadeInput) return;

        // Se já tem poller, apenas atualiza UI se tiver valor no cache
        if (row._pollerId) {
            if (variacaoSelect.value && estoqueCache[variacaoSelect.value] !== undefined) {
                recalcSaldo(row, variacaoSelect.value, tipo, quantidadeInput);
            }
            return;
        }

        // Configura polling para detectar mudança de variação
        let lastVal = variacaoSelect.value;

        row._pollerId = setInterval(() => {
            if (variacaoSelect.value !== lastVal) {
                lastVal = variacaoSelect.value;
                console.log('[EstoqueWidget] Variação mudou:', lastVal);
                onVariacaoChange(row, lastVal, tipo, quantidadeInput);
            }
        }, 300);

        // Listener para quantidade
        quantidadeInput.addEventListener('input', () => {
            recalcSaldo(row, variacaoSelect.value, tipo, quantidadeInput);
        });

        // Se já tem valor, busca
        if (variacaoSelect.value) {
            onVariacaoChange(row, variacaoSelect.value, tipo, quantidadeInput);
        }
    }

    function onVariacaoChange(row, variacaoId, tipo, quantidadeInput) {
        if (!variacaoId) {
            updateUI(row, '-', '-');
            return;
        }

        // Busca do cache ou da API
        if (estoqueCache[variacaoId] !== undefined) {
            recalcSaldo(row, variacaoId, tipo, quantidadeInput);
        } else {
            // Mostra loading só nesta linha
            updateUI(row, '...', '...');
            fetchEstoque(variacaoId, () => {
                recalcSaldo(row, variacaoId, tipo, quantidadeInput);
            });
        }
    }

    function fetchEstoque(variacaoId, callback) {
        fetch(`/estoque/api/saldo-variacao/?variacao_id=${variacaoId}&inventario_id=1`, {
            credentials: 'same-origin'
        })
        .then(r => r.json())
        .then(data => {
            console.log('[EstoqueWidget] Saldo recebido:', data.saldo);
            estoqueCache[variacaoId] = data.saldo ?? 0;
            callback();
        })
        .catch(err => {
            console.error('[EstoqueWidget] Erro:', err);
            estoqueCache[variacaoId] = 0;
            callback();
        });
    }

    function recalcSaldo(row, variacaoId, tipo, quantidadeInput) {
        const saldoAtual = estoqueCache[variacaoId];
        if (saldoAtual === undefined) return;

        const qtd = parseInt(quantidadeInput.value) || 0;
        const saldoApos = tipo === 'entrada' ? saldoAtual + qtd : saldoAtual - qtd;

        updateUI(row, saldoAtual, saldoApos);
    }

    function updateUI(row, saldoAtual, saldoApos) {
        if (!row) return;

        const saEl = row.querySelector('td.field-saldo_atual .readonly');
        const spEl = row.querySelector('td.field-saldo_preview .readonly');

        if (saEl) saEl.textContent = saldoAtual;
        if (spEl) {
            spEl.textContent = saldoApos;
            spEl.classList.remove('saldo-preview-positive', 'saldo-preview-negative', 'saldo-preview-warning');
            if (typeof saldoApos === 'number') {
                if (saldoApos > 0) spEl.classList.add('saldo-preview-positive');
                else if (saldoApos < 0) spEl.classList.add('saldo-preview-negative');
                else spEl.classList.add('saldo-preview-warning');
            }
        }
    }

    // Inicia após DOM ready + delay para select2
    setTimeout(init, 1500);

    window.reinitEstoqueWidget = () => { initialized = false; init(); };
    window.debugEstoqueWidget = () => console.log('Cache:', estoqueCache);
})();
