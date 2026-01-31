
from django.core.management.base import BaseCommand
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.inventario.models import Inventario, InventarioSaldo

class Command(BaseCommand):
    help = "Verifica o status dos produtos para exibição na vitrine."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando verificação de produtos para a vitrine..."))

        produtos = Produto.objects.all().order_by('produto')

        if not produtos.exists():
            self.stdout.write(self.style.WARNING("Nenhum produto encontrado no banco de dados."))
            return

        self.stdout.write(
            f"{'NOME DO PRODUTO':<40} | {'DISPONÍVEL?':<12} | {'ESTOQUE':<10} | {'INVENTÁRIOS NA VITRINE?'}"
        )
        self.stdout.write("-" * 100)

        for produto in produtos:
            estoque_total = produto.estoque
            disponivel = produto.disponivel

            saldos = InventarioSaldo.objects.filter(produto=produto, quantidade__gt=0)
            inventarios_info = []
            inventarios_na_vitrine = False
            if saldos.exists():
                for saldo in saldos:
                    is_vitrine = saldo.inventario.exibir_na_vitrine
                    if is_vitrine:
                        inventarios_na_vitrine = True
                    inventarios_info.append(
                        f"{saldo.inventario.nome} (Vitrine: {is_vitrine}, Qtd: {saldo.quantidade})"
                    )

            status_inventario = ", ".join(inventarios_info)

            # Determina a cor da saída
            if disponivel and estoque_total > 0 and inventarios_na_vitrine:
                style = self.style.SUCCESS
            else:
                style = self.style.ERROR
                if not status_inventario:
                    status_inventario = "Produto sem saldo em nenhum inventário."


            self.stdout.write(style(
                f"{produto.produto:<40} | {str(disponivel):<12} | {str(estoque_total):<10} | {status_inventario}"
            ))

        self.stdout.write("-" * 100)
        self.stdout.write(self.style.SUCCESS("Verificação concluída."))
