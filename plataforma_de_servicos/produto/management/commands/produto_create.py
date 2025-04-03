# ruff: noqa: PLR2004, C901, PLR0912, PLR0915, RUF001

from logging import getLogger

from django.core.management.base import BaseCommand

from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory

logger = getLogger("django")

class Command(BaseCommand):
    help = "Cria produtos aleatoriamente"

    def add_arguments(self, parser):
        parser.add_argument(
            'produto',
            type=str,
            nargs='?',
            help='Nome da produto (opcional)',
        )

    def handle(self, *args, **options):
        produto = options['produto']
        if produto:
            produto = ProdutoFactory.create(produto=produto)
        else:
            produto = ProdutoFactory.create()
        logger.info(f"produto criada: {produto.produto}")
        self.stdout.write(
            self.style.SUCCESS(f"produto criada: {produto.produto}"),
        )
