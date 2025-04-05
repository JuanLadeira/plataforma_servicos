# ruff: noqa: PLR2004, C901, PLR0912, PLR0915, RUF001

from logging import getLogger

from django.core.management.base import BaseCommand

from django.db.utils import IntegrityError
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory
from plataforma_de_servicos.produto.models.produto_model import Produto

logger = getLogger("django")

class Command(BaseCommand):
    help = "Cria produtos aleatoriamente"

    def handle(self, *args, **options):
        while True:
            try:
                logger.info("Tentando criar novo produto...")
                produto = ProdutoFactory.create()
                logger.info(f"Produto criado com sucesso: {produto.produto} (ID: {produto.id})")
                self.stdout.write(
                    self.style.SUCCESS(f"produto criado: {produto.produto}"),
                )
            except IntegrityError as e:
                produtos = Produto.objects.all()
                numero = produtos.count()
                self.stdout.write(
                    self.style.SUCCESS(f"Todos {numero} os produtos foram criados!!"),
                )
                break
            except Exception as e:
                logger.error(f"Erro inesperado ao criar produto: {str(e)}")
                raise
