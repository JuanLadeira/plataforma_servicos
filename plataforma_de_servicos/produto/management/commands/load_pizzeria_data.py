

from logging import getLogger

from django.core.management.base import BaseCommand
from django.db import transaction, connection

from plataforma_de_servicos.produto.models import (
    Categoria,
    Produto,
    Atributo,
    ValorAtributo,
    VariacaoProduto,
)
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.estoque.models import Estoque, EstoqueItens
from plataforma_de_servicos.estoque.choices.movimento import Movimento

logger = getLogger("django")

# --- Dados da Pizzaria ---
CATEGORIAS = ["Pizzas Salgadas", "Pizzas Doces", "Bebidas", "Ingredientes Adicionais"]

TAMANHOS = {
    "Média": {"preco_mod": 0.00, "estoque": 20},
    "Grande": {"preco_mod": 10.00, "estoque": 15},
    "Família": {"preco_mod": 18.00, "estoque": 10},
}

PIZZAS = {
    "Pizzas Salgadas": [
        {"nome": "Pizza de Calabresa", "base_price": 45.00},
        {"nome": "Pizza de Mussarela", "base_price": 42.00},
        {"nome": "Pizza de Frango com Catupiry", "base_price": 52.00},
    ],
    "Pizzas Doces": [
        {"nome": "Pizza de Chocolate com Morango", "base_price": 58.00},
    ],
}

BEBIDAS = [
    {"nome": "Refrigerante 2L", "preco": 12.00, "estoque": 50},
]

ADICIONAIS = [
    {"nome": "Borda de Catupiry", "preco": 8.00, "estoque": 100},
    {"nome": "Extra Bacon", "preco": 6.00, "estoque": 100},
    {"nome": "Cebola Caramelizada", "preco": 4.00, "estoque": 100},
]


class Command(BaseCommand):
    help = "Cria dados de pizzaria com variações de tamanho e ingredientes adicionais."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando criação de dados avançados da pizzaria..."))

        # --- 1. Limpeza ---
        self.stdout.write("Limpando tabelas antigas...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE cart_reservaestoque RESTART IDENTITY CASCADE;")
        except Exception:
            pass
        EstoqueItens.objects.all().delete()
        Estoque.objects.all().delete()
        VariacaoProduto.objects.all().delete()
        ValorAtributo.objects.all().delete()
        Atributo.objects.all().delete()
        Produto.objects.all().delete()
        Categoria.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Dados antigos removidos."))

        # --- 2. Itens Básicos ---
        inventario, _ = Inventario.objects.get_or_create(nome="Inventário Principal")
        cats = {name: Categoria.objects.create(categoria=name) for name in CATEGORIAS}
        self.stdout.write(self.style.SUCCESS("Categorias e Inventário criados."))

        # --- 3. Atributos e Valores ---
        attr_tamanho = Atributo.objects.create(nome="Tamanho")
        valores_tamanho = {
            name: ValorAtributo.objects.create(valor=name, atributo=attr_tamanho)
            for name in TAMANHOS.keys()
        }
        self.stdout.write(self.style.SUCCESS("Atributo 'Tamanho' e seus valores criados."))

        # --- 4. Produtos, Variações e Estoque ---
        entrada_estoque = Estoque.objects.create(
            movimento=Movimento.ENTRADA,
            inventario_destino=inventario,
            observacao="Carga inicial de estoque para pizzaria (com variações)."
        )
        self.stdout.write("Criando produtos, variações e preparando entrada de estoque...")

        # Pizzas com Variações
        for cat_nome, lista_pizzas in PIZZAS.items():
            for pizza_data in lista_pizzas:
                produto_base = Produto.objects.create(
                    produto=pizza_data["nome"],
                    categoria=cats[cat_nome],
                    estoque=0
                )
                total_estoque_base = 0
                for tam_nome, tam_data in TAMANHOS.items():
                    variacao = VariacaoProduto.objects.create(
                        produto=produto_base,
                        preco=pizza_data["base_price"] + tam_data["preco_mod"],
                        estoque=tam_data["estoque"],
                    )
                    variacao.valores.add(valores_tamanho[tam_nome])
                    total_estoque_base += tam_data["estoque"]
                
                # Item de estoque para o PRODUTO BASE com a soma dos estoques das variações
                EstoqueItens.objects.create(
                    estoque=entrada_estoque,
                    produto=produto_base,
                    quantidade=total_estoque_base,
                    inventario=inventario
                )
                self.stdout.write(f"  - Pizza '{pizza_data['nome']}' e suas variações de tamanho criadas.")

        # Bebidas e Adicionais (Produtos Simples)
        produtos_simples = [(BEBIDAS, "Bebidas"), (ADICIONAIS, "Ingredientes Adicionais")]
        for lista, cat_nome in produtos_simples:
            for item_data in lista:
                produto = Produto.objects.create(
                    produto=item_data["nome"],
                    preco=item_data["preco"],
                    categoria=cats[cat_nome],
                    estoque=0
                )
                EstoqueItens.objects.create(
                    estoque=entrada_estoque,
                    produto=produto,
                    quantidade=item_data["estoque"],
                    inventario=inventario
                )
                self.stdout.write(f"  - Item '{item_data['nome']}' criado.")

        # --- 5. Processamento do Estoque ---
        self.stdout.write("Processando a entrada de estoque para atualizar saldos...")
        try:
            entrada_estoque.processar()
            self.stdout.write(self.style.SUCCESS("Entrada de estoque processada!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Falha ao processar o estoque: {e}"))
            raise

        self.stdout.write(self.style.SUCCESS("\nOperação concluída! Dados da pizzaria com variações foram criados."))
