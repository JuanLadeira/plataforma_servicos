import sys

from django.apps import AppConfig


class EmpresaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plataforma_de_servicos.empresa"
    verbose_name = "Empresas"

    def ready(self):
        """Load tenant database connections on app startup."""
        # Skip during migrations, tests, check, or shell_plus
        skip_cmds = ["migrate", "makemigrations", "test", "check", "shell", "shell_plus"]
        # Also skip if pytest is being used
        if any(cmd in sys.argv for cmd in skip_cmds) or "pytest" in sys.argv[0]:
            return

        # Import here to avoid circular imports
        try:
            from plataforma_de_servicos.empresa.services import SchemaManager
            count = SchemaManager.load_all_tenant_connections()
            if count > 0:
                import logging
                logging.getLogger(__name__).info(
                    f"Loaded {count} tenant database connections"
                )
        except Exception:
            # Ignore errors during initial migrations or tests
            pass
