# ruff: noqa: PLR2004, C901, PLR0912, PLR0915, RUF001

from logging import getLogger

from django.core.management.base import BaseCommand

from plataforma_de_servicos.produto.models.produto_model import Produto

logger = getLogger("django")

class Command(BaseCommand):
    help = "Delete um produto especifico"

    def add_arguments(self, parser):
        parser.add_argument(
            'produto',
            type=str,
            nargs='?',
            help='Nome da produto (opcional)',
        )

    def handle(self, *args, **options):
        produto_nome = options['produto']
        if not produto_nome:
            self.stdout.write(
                self.style.ERROR("Nenhum produto especificado"),
            )
            return

        produto = Produto.objects.filter(produto=produto_nome)
        if produto.exists():
            produto.delete()
            logger.info(f"Produto {produto_nome} deletado")
            self.stdout.write(
                self.style.SUCCESS(f"Produto {produto_nome} excluido com sucesso!!"),
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Produto {produto_nome} não existe"),
            )
        
