# ruff: noqa: PLR2003, C901, PLR0912, PLR0915, RUF001
from logging import getLogger

from django.core.management.base import BaseCommand

from plataforma_de_servicos.produto.models.produto_model import Produto

logger = getLogger("django")

class Command(BaseCommand):
    help = "Delete todos os produtos"

    def handle(self, *args, **options):
        produtos = Produto.objects.all()
        numero = produtos.count()
        produtos.delete()
        logger.info(f"Todos os {numero} produtos foram deletadas")
        self.stdout.write(
            self.style.SUCCESS(f"Todos {numero} os produtos foram deletadas!!"),
        )