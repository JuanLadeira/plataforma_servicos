from django.core.management.base import BaseCommand
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.inventario.models import InventarioSaldo

class Command(BaseCommand):
    help = "Atualiza o status de disponibilidade de todos os produtos com base no saldo dos inventários."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando a atualização da disponibilidade dos produtos...")

        produtos_atualizados = 0
        for produto in Produto.objects.all():
            is_disponivel_na_vitrine = InventarioSaldo.objects.filter(
                produto=produto,
                quantidade__gt=0,
                inventario__is_ativo=True,
                inventario__exibir_na_vitrine=True,
            ).exists()

            if produto.disponivel != is_disponivel_na_vitrine:
                produto.disponivel = is_disponivel_na_vitrine
                produto.save(update_fields=["disponivel"])
                produtos_atualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Atualização concluída! {produtos_atualizados} produtos tiveram seu status de disponibilidade atualizado."
            )
        )
