-- Estoque de Produto e VariacaoProduto derivado do InventarioSaldo (issue #144).
-- Placeholders {saldo}, {produto} e {variacao} são trocados pelos nomes das tabelas na migration.

-- Recalcula o estoque da variação e do produto tocados por uma linha de saldo.
-- Variação antes do produto: mesma ordem de travas de estoque/locks.py.
CREATE OR REPLACE FUNCTION sincronizar_estoque_saldo() RETURNS trigger AS $$
DECLARE
    produtos bigint[] := '{{}}';
    variacoes bigint[] := '{{}}';
BEGIN
    -- Saldo novo zerado não muda soma nenhuma; sair cedo evita travar produto e
    -- variação fora da ordem de estoque/locks.py (que cria saldos zerados antes de travá-los).
    IF TG_OP = 'INSERT' AND NEW.quantidade = 0 THEN
        RETURN NULL;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        produtos := produtos || NEW.produto_id;
        variacoes := variacoes || NEW.variacao_id;
    END IF;
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        produtos := produtos || OLD.produto_id;
        variacoes := variacoes || OLD.variacao_id;
    END IF;

    PERFORM set_config('app.sync_saldo', 'on', true);
    UPDATE {variacao} v
       SET estoque = t.total
      FROM (SELECT id, COALESCE((SELECT SUM(s.quantidade) FROM {saldo} s WHERE s.variacao_id = x.id), 0) AS total
              FROM {variacao} x WHERE x.id = ANY(variacoes)) t
     WHERE v.id = t.id AND v.estoque IS DISTINCT FROM t.total;
    UPDATE {produto} p
       SET estoque = t.total
      FROM (SELECT id, COALESCE((SELECT SUM(s.quantidade) FROM {saldo} s WHERE s.produto_id = x.id), 0) AS total
              FROM {produto} x WHERE x.id = ANY(produtos)) t
     WHERE p.id = t.id AND p.estoque IS DISTINCT FROM t.total;
    PERFORM set_config('app.sync_saldo', 'off', true);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Recusa gravar estoque fora do trigger de sincronização.
CREATE OR REPLACE FUNCTION guardar_estoque_derivado() RETURNS trigger AS $$
BEGIN
    IF COALESCE(current_setting('app.sync_saldo', true), 'off') = 'on' THEN
        RETURN NEW;
    END IF;
    IF TG_OP = 'INSERT' AND COALESCE(NEW.estoque, 0) <> 0 THEN
        RAISE EXCEPTION 'estoque de % é derivado do InventarioSaldo e começa em 0; dê saldo por movimentação de estoque', TG_TABLE_NAME
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'UPDATE' AND NEW.estoque IS DISTINCT FROM OLD.estoque THEN
        RAISE EXCEPTION 'estoque de % é derivado do InventarioSaldo; use uma movimentação de estoque', TG_TABLE_NAME
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sincronizar_estoque_saldo
AFTER INSERT OR UPDATE OF quantidade, produto_id, variacao_id OR DELETE ON {saldo}
FOR EACH ROW EXECUTE FUNCTION sincronizar_estoque_saldo();

CREATE TRIGGER guardar_estoque_derivado
BEFORE INSERT OR UPDATE OF estoque ON {produto}
FOR EACH ROW EXECUTE FUNCTION guardar_estoque_derivado();

CREATE TRIGGER guardar_estoque_derivado
BEFORE INSERT OR UPDATE OF estoque ON {variacao}
FOR EACH ROW EXECUTE FUNCTION guardar_estoque_derivado();

-- Acerta todas as linhas uma vez (produtos sem depósito ficam com 0).
SELECT set_config('app.sync_saldo', 'on', true);
UPDATE {variacao} v
   SET estoque = COALESCE((SELECT SUM(s.quantidade) FROM {saldo} s WHERE s.variacao_id = v.id), 0);
UPDATE {produto} p
   SET estoque = COALESCE((SELECT SUM(s.quantidade) FROM {saldo} s WHERE s.produto_id = p.id), 0);
SELECT set_config('app.sync_saldo', 'off', true);
