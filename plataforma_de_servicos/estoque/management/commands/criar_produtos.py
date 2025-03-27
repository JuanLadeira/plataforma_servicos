from django.core.management.base import BaseCommand

from plataforma_de_servicos.produto.create_data import ProdutoClass
from plataforma_de_servicos.produto.create_data import produtos


class Command(BaseCommand):
    help = "Cria produtos no banco de dados"

    def add_arguments(self, parser):
        """
        Adicione argumentos ao comando
        exemplo:
        parser.add_argument('sample_arg', type=str, help='Descrição do argumento')
        """

    def handle(self, *args, **options):
        """
        Handle do comando
        Busca os argumentos e executa a lógica do comando
        exemplo:
        sample_arg = options['sample_arg']
        """
        ProdutoClass.criar_produtos(produtos=produtos)
        self.stdout.write(self.style.SUCCESS("Produtos foram criados."))
