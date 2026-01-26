

from logging import getLogger

from django.core.management.base import BaseCommand
from django.db import transaction, connection

from plataforma_de_servicos.produto.models import Categoria, Produto
from plataforma_de_servicos.inventario.models import Inventario, InventarioSaldo

logger = getLogger("django")

# Nomes de carros e motos para a apresentação
CARROS = [
    {"nome": "Honda Civic Type R", "preco": 350000.00, "estoque": 5},
    {"nome": "Toyota Corolla GR", "preco": 290000.00, "estoque": 8},
    {"nome": "Ford Mustang GT", "preco": 550000.00, "estoque": 3},
    {"nome": "BMW M3", "preco": 700000.00, "estoque": 4},
    {"nome": "Porsche 911 Carrera", "preco": 950000.00, "estoque": 2},
]

MOTOS = [
    {"nome": "Yamaha MT-07", "preco": 45000.00, "estoque": 15},
    {"nome": "Kawasaki Ninja 400", "preco": 38000.00, "estoque": 12},
    {"nome": "Honda CB 650R", "preco": 52000.00, "estoque": 10},
    {"nome": "Ducati Panigale V4", "preco": 180000.00, "estoque": 3},
    {"nome": "BMW S 1000 RR", "preco": 130000.00, "estoque": 5},
]

class Command(BaseCommand):
    help = "Cria um conjunto de produtos (carros e motos) para a apresentação do projeto."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando a criação de dados para apresentação..."))

        # --- Limpando dados antigos ---
        self.stdout.write("Limpando tabelas antigas...")

        # Usando SQL puro para limpar a tabela 'cart_reservaestoque' que não possui mais um modelo.
        try:
            with connection.cursor() as cursor:
                self.stdout.write(self.style.WARNING("  - Limpando 'cart_reservaestoque' com SQL puro..."))
                cursor.execute("TRUNCATE TABLE cart_reservaestoque RESTART IDENTITY CASCADE;")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Não foi possível limpar 'cart_reservaestoque'. Erro: {e}"))
            self.stdout.write(self.style.WARNING("Continuando mesmo assim, pode haver erros de FK..."))


        Produto.objects.all().delete()
        InventarioSaldo.objects.all().delete()
        Categoria.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Dados antigos foram removidos."))

        # --- Criando Categorias ---
        self.stdout.write("Criando categorias 'Carros' e 'Motos'...")
        cat_carros, _ = Categoria.objects.get_or_create(categoria="Carros")
        cat_motos, _ = Categoria.objects.get_or_create(categoria="Motos")
        self.stdout.write(self.style.SUCCESS("Categorias 'Carros' e 'Motos' garantidas."))

        # --- Criando Inventário Principal ---
        self.stdout.write("Garantindo a existência do 'Inventário Principal'...")
        inventario_principal, _ = Inventario.objects.get_or_create(
            nome="Inventário Principal",
            defaults={'is_ativo': True}
        )
        self.stdout.write(self.style.SUCCESS("Inventário 'Inventário Principal' garantido."))


        # --- Criando Produtos ---
        self.stdout.write("Criando produtos da categoria 'Carros'...")
        for carro in CARROS:
            produto_obj = Produto.objects.create(
                produto=carro["nome"],
                preco=carro["preco"],
                estoque=carro["estoque"],  # Mantendo o campo de estoque do produto
                categoria=cat_carros,
            )
            # Criando o saldo no inventário principal
            InventarioSaldo.objects.create(
                inventario=inventario_principal,
                produto=produto_obj,
                quantidade=carro["estoque"]
            )
            self.stdout.write(f"  - Produto '{carro['nome']}' criado com estoque no inventário principal.")

        self.stdout.write("Criando produtos da categoria 'Motos'...")
        for moto in MOTOS:
            produto_obj = Produto.objects.create(
                produto=moto["nome"],
                preco=moto["preco"],
                estoque=moto["estoque"], # Mantendo o campo de estoque do produto
                categoria=cat_motos,
            )
            # Criando o saldo no inventário principal
            InventarioSaldo.objects.create(
                inventario=inventario_principal,
                produto=produto_obj,
                quantidade=moto["estoque"]
            )
            self.stdout.write(f"  - Produto '{moto['nome']}' criado com estoque no inventário principal.")

        total_produtos = Produto.objects.count()
        self.stdout.write(self.style.SUCCESS(f"\nOperação concluída! {total_produtos} produtos foram criados."))
