import sys

from django.core.management.base import BaseCommand

from plataforma_de_servicos.estoque import saldos
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto

LIMITE = 50


class Command(BaseCommand):
    help = (
        "Lista saldos de estoque negativos, duplicados e divergentes. "
        "Com --corrigir, junta duplicados, recalcula produto e variação pela soma dos depósitos e dá "
        "entrada no depósito padrão para produtos com estoque e sem depósito. "
        "Sai com código 1 quando encontra algum problema."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa", help="slug da empresa (padrão: todas)")
        parser.add_argument(
            "--corrigir",
            action="store_true",
            help="junta duplicados, recalcula pelas somas e dá entrada para produtos sem depósito",
        )

    def handle(self, *args, empresa=None, corrigir=False, **options):
        if corrigir:
            sem_padrao = saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo, empresa)
            for produto in sem_padrao:
                self.stdout.write(
                    self.style.WARNING(
                        f"produto #{produto.pk} {produto.produto}: sem depósito e a empresa não tem "
                        "depósito padrão; marque um e rode de novo"
                    )
                )
            self.stdout.write("Correção aplicada. Verificando de novo...")
        if self._relatorio(empresa):
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("Nenhum problema de saldo encontrado."))

    def _secao(self, titulo, linhas):
        linhas = list(linhas)
        if not linhas:
            return 0
        self.stdout.write(self.style.WARNING(f"{titulo}: {len(linhas)}"))
        for linha in linhas[:LIMITE]:
            self.stdout.write(f"  {linha}")
        if len(linhas) > LIMITE:
            self.stdout.write(f"  ... e mais {len(linhas) - LIMITE}")
        return len(linhas)

    def _relatorio(self, empresa):
        problemas = 0
        problemas += self._secao(
            "Saldo negativo em depósito",
            (
                f"saldo #{s.pk} depósito={s.inventario_id} produto={s.produto_id} "
                f"variação={s.variacao_id} quantidade={s.quantidade}"
                for s in saldos.saldos_negativos(InventarioSaldo, empresa)
            ),
        )
        problemas += self._secao(
            "Estoque negativo em produto",
            (
                f"produto #{p.pk} {p.produto}: {p.estoque}"
                for p in saldos.produtos_negativos(Produto, empresa)
            ),
        )
        problemas += self._secao(
            "Saldo duplicado em depósito",
            (
                f"depósito={d['inventario_id']} produto={d['produto_id']} "
                f"variação={d['variacao_id']} registros={d['n']}"
                for d in saldos.saldos_duplicados(InventarioSaldo, empresa)
            ),
        )
        problemas += self._secao(
            "Variação divergente da soma dos depósitos",
            (
                f"variação #{v.pk}: estoque={v.estoque} depósitos={v.total_depositos}"
                for v in saldos.variacoes_divergentes(
                    VariacaoProduto, InventarioSaldo, empresa
                )
            ),
        )
        problemas += self._secao(
            "Produto divergente da soma dos depósitos",
            (
                f"produto #{p.pk} {p.produto}: estoque={p.estoque} depósitos={p.total_depositos}"
                for p in saldos.produtos_divergentes(Produto, InventarioSaldo, empresa)
            ),
        )
        # A migration da fonte única de saldo (#144) não roda com estes casos.
        problemas += self._secao(
            "Produto com estoque e sem nenhum depósito (--corrigir dá entrada no depósito padrão)",
            (
                f"produto #{p.pk} {p.produto}: estoque={p.estoque}"
                for p in saldos.produtos_sem_deposito(Produto, InventarioSaldo, empresa)
            ),
        )
        return problemas
