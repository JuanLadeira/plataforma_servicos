# ruff: noqa: PLR2004, C901, PLR0912, PLR0915, RUF001

from logging import getLogger

from django.core.management.base import BaseCommand

from plataforma_de_servicos.produto.tests.factories.categoria_factory import CategoriaFactory

logger = getLogger("django")

class Command(BaseCommand):
    help = "Cria categorias aleatoriamente"

    def add_arguments(self, parser):
        parser.add_argument(
            'categoria',
            type=str,
            nargs='?',
            help='Nome da Categoria (opcional)',
        )

    def handle(self, *args, **options):
        categoria = options['categoria']
        if categoria:
            categoria = CategoriaFactory.create(categoria=categoria)
        else:
            categoria = CategoriaFactory.create()
        logger.info(f"Categoria criada: {categoria.categoria}")
        self.stdout.write(
            self.style.SUCCESS(f"Categoria criada: {categoria.categoria}"),
        )
