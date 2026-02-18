"""
Management command to apply migrations to all dedicated tenant schemas.
"""
from django.core.management.base import BaseCommand

from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.empresa.models import TipoIsolamento
from plataforma_de_servicos.empresa.services import SchemaManager
from plataforma_de_servicos.empresa.services import SchemaManagerError


class Command(BaseCommand):
    help = "Apply migrations to all dedicated tenant schemas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa",
            type=str,
            help="Migrate only this empresa's schema (by slug)",
        )

    def handle(self, *args, **options):
        empresa_slug = options.get("empresa")

        if empresa_slug:
            # Migrate single empresa
            try:
                empresa = Empresa.objects.get(slug=empresa_slug)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Empresa '{empresa_slug}' not found")
                )
                return

            if not empresa.schema_criado:
                self.stdout.write(
                    self.style.ERROR(
                        f"Empresa '{empresa_slug}' does not have a provisioned schema"
                    )
                )
                return

            self._migrate_empresa(empresa)
            return

        # Migrate all dedicated tenants
        empresas = Empresa.objects.filter(
            tipo_isolamento=TipoIsolamento.DEDICADO,
            schema_criado=True,
        )

        if not empresas.exists():
            self.stdout.write("No tenants with dedicated database found")
            return

        self.stdout.write(f"Found {empresas.count()} tenant(s) to migrate\n")

        success_count = 0
        error_count = 0

        for empresa in empresas:
            if self._migrate_empresa(empresa):
                success_count += 1
            else:
                error_count += 1

        self.stdout.write(f"\nMigration complete: {success_count} success, {error_count} errors")

    def _migrate_empresa(self, empresa):
        """Migrate a single empresa's schema. Returns True on success."""
        self.stdout.write(f"\nMigrating: {empresa.slug} ({empresa.schema_name})")

        try:
            SchemaManager.migrate_schema(empresa)
            self.stdout.write(self.style.SUCCESS("  Done"))
            return True
        except SchemaManagerError as e:
            self.stdout.write(self.style.ERROR(f"  Error: {e}"))
            return False
