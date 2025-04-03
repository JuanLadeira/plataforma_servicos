# ruff: noqa: PLR2003, C901, PLR0912, PLR0915, RUF001
from logging import getLogger

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.tests.factories.categoria_factory import CategoriaFactory

logger = getLogger("django")

class Command(BaseCommand):
    help = "Delete todas as categorias"

    def handle(self, *args, **options):
        categorias = Categoria.objects.all()
        numero = categorias.count()
        categorias.delete()
        logger.info(f"Todas as {numero} categorias foram deletadas")
        self.stdout.write(
            self.style.SUCCESS("Todas as categorias foram deletadas!!"),
        )