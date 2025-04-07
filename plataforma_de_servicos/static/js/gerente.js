document.addEventListener('DOMContentLoaded', function() {
    // Verifica se está na página do EstoqueSaidaAdmin
    const isEstoqueSaidaPage = document.querySelector('body.model-estoquesaida');
    
    if (isEstoqueSaidaPage) {
        // Altera cores das linhas da tabela
        const tableRows = document.querySelectorAll('.unfold-table tbody tr');
        tableRows.forEach(row => {
            row.style.backgroundColor = 'rgba(255, 200, 200, 0.2)'; // Vermelho claro
            row.style.borderLeft = '4px solid rgb(255, 0, 0)'; // Borda vermelha
        });

        // Altera cor do cabeçalho da tabela
        const tableHeader = document.querySelector('.unfold-table thead');
        if (tableHeader) {
            tableHeader.style.backgroundColor = 'rgb(0, 100, 0)'; // Verde escuro
            tableHeader.style.color = 'white';
        }

        // Altera placeholders (se houver inputs)
        const inputs = document.querySelectorAll('input::placeholder');
        inputs.forEach(input => {
            input.style.color = 'rgb(169, 169, 169)'; // Cinza
        });
    }
});