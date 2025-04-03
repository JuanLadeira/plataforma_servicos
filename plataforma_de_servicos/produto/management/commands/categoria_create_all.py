# ruff: noqa: PLR2004, C901, PLR0912, PLR0915, RUF001

from logging import getLogger

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.tests.factories.categoria_factory import CategoriaFactory

logger = getLogger("django")

class Command(BaseCommand):
    help = "Cria categorias aleatoriamente"

    def handle(self, *args, **options):
        while True:
            try:
                categoria = CategoriaFactory.create()
                logger.info(f"Categoria criada: {categoria.categoria}")
                self.stdout.write(
                    self.style.SUCCESS(f"Categoria criada: {categoria.categoria}"),
                )
            except ValueError:
                logger.warning("Todas as categorias foram criadas")
                self.stdout.write(
                    self.style.SUCCESS("Todas as Categorias foram criadas!!"),
                )
                break
      