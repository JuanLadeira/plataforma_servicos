/**
 * JavaScript para o formulário standalone de VariacaoProduto.
 * Atualiza dinamicamente os valores de atributos quando o produto é alterado.
 */
(function($) {
    'use strict';

    // Aguarda o Django admin estar pronto
    $(document).ready(function() {
        initVariacaoForm();
    });

    function initVariacaoForm() {
        // Encontra o campo de produto
        var $produtoSelect = $('select[name="produto"]');
        var $valoresContainer = $('.valores-atributo-container');

        console.log('variacao-produto-form.js: Inicializando...');
        console.log('$produtoSelect encontrado:', $produtoSelect.length > 0);
        console.log('$valoresContainer encontrado:', $valoresContainer.length > 0);

        if ($produtoSelect.length === 0) {
            console.log('Campo produto não encontrado');
            return;
        }

        if ($valoresContainer.length === 0) {
            console.log('Container de valores não encontrado');
            return;
        }

        // Função para buscar os valores de atributos para um produto
        function fetchValoresForProduto(produtoId) {
            console.log('Buscando atributos para produto:', produtoId);

            if (!produtoId) {
                showEmptyState();
                return;
            }

            var url = '/gerentes/api/produto/' + produtoId + '/atributos/';
            console.log('Fazendo requisição para:', url);

            $.ajax({
                url: url,
                method: 'GET',
                dataType: 'json',
                success: function(data) {
                    console.log('Dados recebidos:', data);
                    renderValores(data);
                },
                error: function(xhr, status, error) {
                    console.error('Erro ao buscar atributos:', status, error);
                    console.error('Response:', xhr.responseText);
                    showEmptyState('Erro ao buscar atributos. Recarregue a página.');
                }
            });
        }

        // Função para mostrar estado vazio
        function showEmptyState(message) {
            var msg = message || 'Selecione um produto primeiro para ver os atributos disponíveis.';
            $valoresContainer.html(
                '<div class="valores-empty-state">' +
                '<span class="empty-message">' + msg + '</span>' +
                '</div>'
            );
        }

        // Função para renderizar os valores
        function renderValores(data) {
            if (!data.atributos || data.atributos.length === 0) {
                $valoresContainer.html(
                    '<div class="valores-empty-state">' +
                    '<span class="empty-message">Nenhum atributo disponível para a categoria deste produto.</span>' +
                    '</div>'
                );
                return;
            }

            var currentValues = getSelectedValues();
            var html = '';

            $.each(data.atributos, function(i, atributo) {
                var multiplaSelecao = atributo.multipla_selecao;
                var selectionHint = multiplaSelecao ? '' : ' <span class="selection-hint">(escolha 1)</span>';

                html += '<div class="atributo-group" data-multipla="' + multiplaSelecao + '">';
                html += '<span class="atributo-label">' + escapeHtml(atributo.nome) + selectionHint + '</span>';
                html += '<div class="valores-chips">';

                $.each(atributo.valores, function(j, valor) {
                    var isChecked = currentValues.indexOf(String(valor.id)) !== -1;
                    var checkedAttr = isChecked ? 'checked' : '';
                    var checkedClass = isChecked ? 'checked' : '';

                    html += '<label class="valor-chip ' + checkedClass + '" for="valores_' + valor.id + '">';
                    html += '<input type="checkbox" name="valores" value="' + valor.id + '" ';
                    html += 'id="valores_' + valor.id + '" ' + checkedAttr + ' class="valor-checkbox" ';
                    html += 'data-atributo="' + escapeHtml(atributo.nome) + '" data-multipla="' + multiplaSelecao + '">';
                    html += '<span class="chip-text">' + escapeHtml(valor.valor) + '</span>';
                    html += '</label>';
                });

                html += '</div></div>';
            });

            // Links para adicionar atributo/valor
            if (data.categoria_id) {
                html += '<div class="valores-add-links">';
                html += '<a href="/gerentes/produto/atributo/add/?_categoria=' + data.categoria_id + '" ';
                html += 'class="add-link add-atributo-link" target="_blank" ';
                html += 'title="Criar novo atributo (ex: Cor, Tamanho)">';
                html += '<span class="add-icon">+</span> Novo Atributo</a>';
                html += '<a href="/gerentes/produto/valoratributo/add/?_categoria=' + data.categoria_id + '" ';
                html += 'class="add-link add-valor-link" target="_blank" ';
                html += 'title="Criar novo valor para um atributo existente">';
                html += '<span class="add-icon">+</span> Novo Valor</a>';
                html += '</div>';
            }

            $valoresContainer.html(html);

            // Re-inicializa os event listeners dos chips
            initChipListeners();
        }

        // Função para obter valores selecionados atualmente
        function getSelectedValues() {
            var values = [];
            $valoresContainer.find('input[name="valores"]:checked').each(function() {
                values.push($(this).val());
            });
            return values;
        }

        // Função para inicializar listeners nos chips
        function initChipListeners() {
            $valoresContainer.find('.valor-checkbox').on('change', function() {
                var $this = $(this);
                var $chip = $this.closest('.valor-chip');

                if ($this.is(':checked')) {
                    $chip.addClass('checked');

                    // Se não permite múltipla seleção, desmarca outros do mesmo atributo
                    if ($this.data('multipla') === false || $this.data('multipla') === 'false') {
                        var atributo = $this.data('atributo');
                        $valoresContainer.find('.valor-checkbox').each(function() {
                            var $other = $(this);
                            if ($other[0] !== $this[0] && $other.data('atributo') === atributo && $other.is(':checked')) {
                                $other.prop('checked', false);
                                $other.closest('.valor-chip').removeClass('checked');
                            }
                        });
                    }
                } else {
                    $chip.removeClass('checked');
                }
            });
        }

        // Função auxiliar para escape de HTML
        function escapeHtml(text) {
            if (!text) return '';
            return $('<div>').text(text).html();
        }

        // Handler para mudança de produto
        function handleProdutoChange() {
            var produtoId = $produtoSelect.val();
            console.log('Produto alterado para:', produtoId);
            if (produtoId) {
                fetchValoresForProduto(produtoId);
            } else {
                showEmptyState();
            }
        }

        // ============================================
        // CAPTURA DE EVENTOS DO SELECT2/AUTOCOMPLETE
        // ============================================

        // 1. Evento change nativo
        $produtoSelect.on('change', function() {
            console.log('Evento change jQuery disparado');
            handleProdutoChange();
        });

        // 2. Eventos específicos do Select2
        $produtoSelect.on('select2:select', function(e) {
            console.log('Evento select2:select disparado');
            handleProdutoChange();
        });

        $produtoSelect.on('select2:clear', function(e) {
            console.log('Evento select2:clear disparado');
            showEmptyState();
        });

        // 3. MutationObserver para detectar mudanças no DOM (fallback)
        var selectElement = $produtoSelect[0];
        if (selectElement) {
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'childList' || mutation.type === 'attributes') {
                        console.log('MutationObserver detectou mudança no select');
                        var currentValue = $produtoSelect.val();
                        if (currentValue && currentValue !== observer.lastValue) {
                            observer.lastValue = currentValue;
                            handleProdutoChange();
                        }
                    }
                });
            });

            observer.lastValue = $produtoSelect.val();
            observer.observe(selectElement, {
                childList: true,
                attributes: true,
                attributeFilter: ['value']
            });

            console.log('MutationObserver configurado');
        }

        // 4. Observa também o container do Select2 (se existir)
        setTimeout(function() {
            var $select2Container = $produtoSelect.siblings('.select2-container');
            if ($select2Container.length > 0) {
                console.log('Container Select2 encontrado, observando cliques');

                // Observa o span de seleção do Select2
                $select2Container.on('click', '.select2-selection', function() {
                    console.log('Clique no Select2 detectado');
                });

                // Polling como último recurso
                var lastValue = $produtoSelect.val();
                setInterval(function() {
                    var currentValue = $produtoSelect.val();
                    if (currentValue !== lastValue) {
                        console.log('Polling detectou mudança de', lastValue, 'para', currentValue);
                        lastValue = currentValue;
                        if (currentValue) {
                            handleProdutoChange();
                        } else {
                            showEmptyState();
                        }
                    }
                }, 500);
            }
        }, 1000);

        // Estado inicial
        var currentValue = $produtoSelect.val();
        if (currentValue) {
            console.log('Produto já selecionado, inicializando listeners:', currentValue);
            // Na edição, os valores já estão renderizados pelo servidor
            initChipListeners();
        } else {
            console.log('Nenhum produto selecionado, mostrando estado vazio');
            showEmptyState();
        }

        console.log('variacao-produto-form.js: Inicialização completa');
    }

})(django.jQuery || jQuery);
