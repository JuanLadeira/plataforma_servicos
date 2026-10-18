# Spec: saldo de estoque seguro sob concorrência

- **Issue:** #141
- **Data:** 18/10/2026
- **Status:** rascunho, aguardando revisão do Juan
- **Escopo escolhido:** passos 1 a 4 da #141 e o bug do inventário de outra empresa. A fonte única de saldo (passo 5, card t29) fica para uma spec própria.

## 1. Problema

Toda movimentação de estoque grava o saldo em três lugares: `Produto.estoque`, `VariacaoProduto.estoque` e `InventarioSaldo.quantidade`. Só o último usa trava. Com duas operações ao mesmo tempo, o sistema pode:

- processar a mesma movimentação duas vezes;
- perder uma baixa em produto ou variação, ou aprovar uma saída sem saldo;
- sobrescrever campos do produto editados no mesmo instante, porque grava com `save()` completo;
- aprovar a mesma ordem duas vezes, gerando duas saídas e duas comissões;
- deixar saldo de depósito negativo.

Há também um bug que não depende de concorrência: a saída da ordem aprovada usa `Inventario.objects.first()`, ou seja, o inventário criado por último no banco, de **qualquer** empresa (`estoque/services.py:38`).

## 2. Objetivos

1. Uma movimentação nunca é aplicada mais de uma vez.
2. Operações simultâneas sobre o mesmo item terminam com os três saldos corretos e iguais.
3. Nenhuma saída deixa saldo negativo em produto, variação ou depósito.
4. Uma ordem só é aprovada uma vez, com uma saída e uma comissão.
5. A baixa da ordem sai sempre do depósito padrão **da empresa da ordem**.
6. O banco recusa saldo negativo e saldo duplicado, mesmo que o código erre.

## 3. Fora do escopo

- Fonte única de saldo (t29).
- Estorno de estoque e comissão ao cancelar uma ordem aprovada (t44).
- Corrida na numeração de leads e ordens (t32).
- Escolha manual do depósito ou divisão da baixa entre depósitos.

## 4. Decisões já tomadas

| Pergunta | Decisão |
|---|---|
| Escopo | Travas, aprovação atômica, constraints e bug do inventário |
| Depósito da baixa da ordem | Depósito padrão, um por empresa |
| Dados negativos existentes | A migration para e lista os registros; corrige-se antes de reaplicar |
| Técnica contra concorrência | Trava pessimista (`select_for_update`) em ordem fixa |

## 5. Design

### 5.1 Depósito padrão por empresa

- Novo campo `Inventario.padrao = BooleanField(default=False)`.
- `UniqueConstraint(fields=["empresa"], condition=Q(padrao=True), name="unique_inventario_padrao_por_empresa")`: no máximo um padrão por empresa.
- `Inventario.clean()`: um depósito padrão precisa estar ativo.
- Helper `Inventario.objects.padrao_da_empresa(empresa)` que levanta `InventarioPadraoAusenteError` com mensagem clara quando a empresa não tem padrão.
- Migration de dados: em cada empresa sem padrão, marcar o inventário ativo com `exibir_na_vitrine=True` mais antigo; se não houver, o ativo mais antigo; se não houver nenhum ativo, deixar sem padrão. Nesse último caso a aprovação de ordem dessa empresa falha com a mensagem do helper até alguém marcar um.
- O campo aparece no admin de inventário do portal de gerentes. Marcar um novo padrão desmarca o anterior na mesma transação.

### 5.2 Ordem fixa de travas

Novo módulo `estoque/locks.py` com uma função que recebe os itens de uma movimentação e trava, sempre nesta ordem:

1. a linha da movimentação (`Estoque`);
2. as linhas de `InventarioSaldo` envolvidas, ordenadas por `(inventario_id, produto_id, variacao_id)`;
3. as `VariacaoProduto`, ordenadas por `pk`;
4. os `Produto`, ordenados por `pk`.

A função devolve as instâncias travadas indexadas por chave. Assim, vários itens da mesma variação na mesma movimentação compartilham a mesma instância e acumulam corretamente.

Toda transação que mexe em saldo passa por essa função. A ordem fixa impede deadlock entre duas operações.

As transações que travam saldo executam `SET LOCAL lock_timeout = '5s'`. Se algo segurar uma trava por tempo anormal, a operação falha com erro claro em vez de ficar pendurada.

### 5.3 `Estoque.processar()`

Fluxo novo, todo dentro de `transaction.atomic()`:

1. Recarregar a movimentação com `select_for_update()`. Se `processado` já for verdadeiro, sair sem fazer nada.
2. Travar os saldos (5.2).
3. Para cada item, calcular o novo saldo sobre os valores travados:
   - **Entrada:** soma em produto, variação e no depósito de destino.
   - **Saída:** subtrai dos três. Se qualquer um ficar negativo, levanta o erro de saldo insuficiente correspondente: `ProdutoSaldoInsuficienteError`, `VariacaoSaldoInsuficienteError` ou o novo `InventarioSaldoInsuficienteError`. Hoje a saída de um depósito sem saldo cria o registro com zero ou deixa negativo; com a mudança, ela é recusada.
   - **Transferência:** produto e variação não mudam; subtrai do depósito de origem, com a mesma checagem, e soma no de destino.
4. Gravar `saldo_anterior` e `saldo` do item a partir dos valores travados.
5. Salvar produto e variação com `save(update_fields=["estoque"])`; nunca `save()` completo.
6. Marcar `processado=True` com `save(update_fields=["processado"])`.

`InventarioSaldo` que ainda não existe é criado dentro da trava. Se outra transação criar o mesmo registro antes, o `IntegrityError` da constraint única é tratado relendo o registro com `select_for_update()`.

O signal que recalcula `Produto.disponivel` continua como está.

### 5.4 Aprovação e transições da ordem

`OrdemCompraService.aprovar` passa a ser uma única transação:

1. Recarregar a ordem com `select_for_update()` e checar `pode_aprovar` no registro travado. Uma segunda aprovação simultânea espera e depois falha com "não pode ser aprovada".
2. Obter o depósito padrão da empresa da ordem (5.1).
3. Criar a saída com `inventario_origem` igual ao depósito padrão e processá-la (5.3). A checagem de saldo insuficiente acontece sobre os valores travados, inclusive o saldo **do depósito padrão**.
4. Atualizar status, `aprovado_por` e `data_aprovacao`.
5. Criar a comissão.

Qualquer erro desfaz tudo: sem saída, sem status novo e sem comissão.

`validar_estoque`, usado para exibir disponibilidade antes de aprovar, passa a consultar o saldo do depósito padrão, para mostrar o mesmo número que a aprovação vai checar. Em `criar_ordem_manual`, quando `inventario_origem_id` não é informado, a validação também usa o depósito padrão.

`rejeitar`, `faturar`, `cancelar` e `concluir` recebem o mesmo tratamento: transação, ordem recarregada com `select_for_update()` e checagem de status no registro travado.

`EstoqueService.criar_saida_por_ordem_compra` deixa de ter o fallback `Inventario.objects.first()` e passa a exigir o depósito. `criar_saida_manual` também passa a exigir o depósito e grava `empresa` a partir dele; hoje cria a movimentação sem empresa.

### 5.5 Constraints no banco

Numa migration:

- `CheckConstraint(quantidade >= 0)` em `InventarioSaldo`.
- `CheckConstraint(estoque >= 0)` em `Produto`. O campo aceita nulo, e nulo continua aceito.
- `VariacaoProduto.estoque` já é `PositiveIntegerField`, que no Postgres já tem a checagem.
- Trocar `unique_together = ("inventario", "produto", "variacao")` de `InventarioSaldo` por `UniqueConstraint(..., nulls_distinct=False)`. Hoje o Postgres trata os nulos como diferentes, então podem existir dois saldos do mesmo produto sem variação no mesmo depósito. Isso exige Postgres 15 ou superior; o projeto usa o 16.

Antes de aplicar as constraints, um `RunPython` procura saldos negativos e saldos duplicados. Se encontrar algum, a migration falha listando até 20 registros e pede para rodar `manage.py verificar_saldos`.

### 5.6 Comando `verificar_saldos`

`manage.py verificar_saldos [--empresa SLUG] [--corrigir]`

O comando lista:

- saldos negativos nos três lugares;
- `InventarioSaldo` duplicados;
- divergências entre `VariacaoProduto.estoque` e a soma dos `InventarioSaldo` daquela variação;
- divergências entre `Produto.estoque` e a soma dos `InventarioSaldo` daquele produto.

Com `--corrigir`, o comando:

- recalcula `Produto.estoque` e `VariacaoProduto.estoque` a partir da soma dos depósitos;
- junta os `InventarioSaldo` duplicados, somando as quantidades;
- **não** mexe em saldo negativo de depósito. Esses casos são listados para correção por movimentação de entrada, que deixa histórico.

Sem `--corrigir`, o comando só lê e termina com código de saída 1 quando encontra algum problema. Assim ele serve de checagem em deploy.

## 6. Erros e mensagens

| Situação | Erro | Onde aparece |
|---|---|---|
| Empresa sem depósito padrão | `InventarioPadraoAusenteError` | Mensagem no admin ao aprovar |
| Saldo insuficiente no depósito | `InventarioSaldoInsuficienteError` | Mensagem no admin com produto, depósito e saldo |
| Ordem já aprovada por outra pessoa | `OrdemCompraServiceError` | "Ordem X não pode ser aprovada. Status atual: Aprovada" |
| Trava presa além de 5 s | `OperationalError` do lock_timeout | Mensagem genérica "tente de novo" |

## 7. Testes

**Concorrência real.** Os testes usam `@pytest.mark.django_db(transaction=True)` e duas threads, cada uma com conexão própria, sincronizadas por `threading.Barrier`:

1. Processar a mesma movimentação em paralelo: o saldo é aplicado uma vez.
2. Duas saídas simultâneas da mesma variação: os três saldos terminam iguais e corretos.
3. Duas saídas simultâneas cuja soma passa do saldo: uma passa e a outra falha, sem negativo.
4. Duas aprovações simultâneas da mesma ordem: uma saída e uma comissão.
5. Movimentações cruzadas com os mesmos itens em ordem inversa: terminam sem deadlock.

**Unidade e integração:**

- A saída da ordem usa o depósito padrão da empresa da ordem, nunca o de outra empresa.
- Aprovação sem depósito padrão falha e não grava nada.
- Saída maior que o saldo do depósito falha mesmo com saldo total suficiente.
- Transferência sem saldo na origem falha.
- `save` de produto durante a baixa não sobrescreve outros campos.
- A migration falha com saldo negativo ou duplicado e passa sem eles.
- `verificar_saldos` lista e corrige os casos descritos em 5.6.
- Os testes existentes de estoque, inventário e vendas continuam passando.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Deadlock entre transações | Ordem fixa de travas (5.2), coberta pelo teste 5 |
| Operação pendurada esperando trava | `lock_timeout` de 5 s |
| Saída que antes "passava" agora é recusada por falta de saldo no depósito | Comportamento correto; a mensagem diz o depósito e o saldo. Rodar `verificar_saldos` antes do deploy |
| Migration falha em produção por dados ruins | É a decisão tomada; o comando mostra o que corrigir |
| Empresa sem inventário ativo fica sem depósito padrão | A aprovação mostra a mensagem do helper; o gerente marca um padrão |

## 9. Entrega

Um PR com os passos 1 a 4, em commits separados por parte: depósito padrão, travas em `processar`, aprovação atômica, constraints e comando. O plano de implementação detalha a ordem e os testes de cada passo, escrevendo os testes primeiro.
