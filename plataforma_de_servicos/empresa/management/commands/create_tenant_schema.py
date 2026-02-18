"""
Management command to create PostgreSQL schema for a dedicated tenant.
"""
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.empresa.models import TipoIsolamento
from plataforma_de_servicos.empresa.services import SchemaManager
from plataforma_de_servicos.empresa.services import SchemaManagerError


class Command(BaseCommand):
    help = "Create PostgreSQL schema for empresa with dedicated database"

    def add_arguments(self, parser):
        parser.add_argument(
            "empresa_slug",
            type=str,
            help="Slug of the empresa",
        )

    def handle(self, *args, **options):
        slug = options["empresa_slug"]

        try:
            empresa = Empresa.objects.get(slug=slug)
        except Empresa.DoesNotExist:
            raise CommandError(f"Empresa '{slug}' not found")

        if empresa.tipo_isolamento != TipoIsolamento.DEDICADO:
            raise CommandError(
                f"Empresa '{slug}' is not configured for dedicated database. "
                f"Current type: {empresa.get_tipo_isolamento_display()}"
            )

        if empresa.schema_criado:
            self.stdout.write(
                self.style.WARNING(
                    f"Schema already exists: {empresa.schema_name}"
                )
            )
            return

        try:
            schema_name = SchemaManager.create_schema(empresa)
            self.stdout.write(
                self.style.SUCCESS(f"Schema created: {schema_name}")
            )
        except SchemaManagerError as e:
            raise CommandError(str(e))
