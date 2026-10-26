from django.core.management.base import BaseCommand
from django.db import transaction

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.choices.origem_saida import OrigemSaida
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.comissao import StatusComissao
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    ComissaoPagaError,
)
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)

MOTIVO = "correção de cancelamento antigo"


class Command(BaseCommand):
    help = (
        "Lista ordens canceladas antes da correção da #146, que ficaram com a baixa de "
        "estoque e a comissão. Com --aplicar, devolve o estoque e cancela as comissões. "
        "Ordens com comissão já paga são puladas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa", help="slug da empresa (padrão: todas)")
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="devolve o estoque e cancela as comissões (sem isso, só lista)",
        )

    def handle(self, *args, empresa=None, aplicar=False, **options):
        ordens = self._pendentes(empresa)
        if not ordens:
            self.stdout.write(
                self.style.SUCCESS("Nenhuma ordem cancelada sem estorno.")
            )
            return

        self.stdout.write(
            self.style.WARNING(f"Ordens canceladas sem estorno: {len(ordens)}")
        )
        for ordem in ordens:
            if aplicar:
                self._aplicar(ordem)
            else:
                self.stdout.write(f"  {self._descrever(ordem)}")
        if not aplicar:
            self.stdout.write(
                "Nada foi alterado. Rode de novo com --aplicar para corrigir."
            )

    def _pendentes(self, empresa):
        saidas = Estoque.objects.filter(
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PEDIDO.value,
            processado=True,
            estorno__isnull=True,
            ordem_compra__status=StatusOrdemCompra.CANCELADA,
        )
        if empresa:
            saidas = saidas.filter(ordem_compra__empresa__slug=empresa)
        ids = saidas.values_list("ordem_compra_id", flat=True)
        return list(
            OrdemCompra.objects.filter(pk__in=ids)
            .select_related("empresa")
            .order_by("pk")
        )

    def _descrever(self, ordem):
        comissoes = ordem.comissoes.exclude(status=StatusComissao.CANCELADA)
        paga = any(c.status == StatusComissao.PAGA for c in comissoes)
        resumo = f"{ordem.numero} ({ordem.empresa}): {comissoes.count()} comissão(ões) ativa(s)"
        return resumo + ("; comissão paga, será pulada" if paga else "")

    def _aplicar(self, ordem):
        try:
            with transaction.atomic():
                travada = OrdemCompra.objects.select_for_update().get(pk=ordem.pk)
                OrdemCompraService.desfazer_aprovacao(travada, MOTIVO)
        except ComissaoPagaError:
            self.stdout.write(
                self.style.ERROR(f"  {ordem.numero}: pulada, comissão já paga")
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"  {ordem.numero}: estoque devolvido e comissões canceladas"
            )
        )
