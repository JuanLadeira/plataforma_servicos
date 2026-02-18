"""
Service for managing PostgreSQL schemas for dedicated tenant databases.
"""
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db import connections
from django.utils import timezone

if TYPE_CHECKING:
    from plataforma_de_servicos.empresa.models import Empresa

logger = logging.getLogger(__name__)


class SchemaManagerError(Exception):
    """Error in schema management."""

    pass


class SchemaManager:
    """
    Manages PostgreSQL schema lifecycle for dedicated tenants.

    Operations:
    - create_schema: Creates schema and applies migrations
    - delete_schema: Removes schema (CAUTION!)
    - migrate_schema: Applies pending migrations
    - register_connection: Dynamically registers database connection
    """

    # Apps that receive migrations in tenant schema
    TENANT_APPS = ["produto", "inventario", "estoque", "vendas", "corretor", "servico", "payment", "cart"]

    @classmethod
    def generate_schema_name(cls, empresa: "Empresa") -> str:
        """Generate schema name from empresa slug."""
        return f"tenant_{empresa.slug.replace('-', '_').lower()}"

    @classmethod
    def create_schema(cls, empresa: "Empresa") -> str:
        """
        Create PostgreSQL schema for the empresa.

        Args:
            empresa: Empresa instance with tipo_isolamento=DEDICADO

        Returns:
            Name of created schema

        Raises:
            SchemaManagerError: If empresa is not properly configured
        """
        from plataforma_de_servicos.empresa.models import TipoIsolamento

        if empresa.tipo_isolamento != TipoIsolamento.DEDICADO:
            raise SchemaManagerError(
                f"Empresa {empresa.slug} is not configured for dedicated database"
            )

        if empresa.schema_criado:
            raise SchemaManagerError(
                f"Schema already exists for {empresa.slug}: {empresa.schema_name}"
            )

        # Generate schema name if not defined
        schema_name = empresa.schema_name or cls.generate_schema_name(empresa)

        try:
            # 1. Create schema in PostgreSQL
            with connection.cursor() as cursor:
                # Use quote_ident to prevent SQL injection
                cursor.execute(
                    "SELECT format('CREATE SCHEMA IF NOT EXISTS %I', %s)",
                    [schema_name]
                )
                create_sql = cursor.fetchone()[0]
                cursor.execute(create_sql)

            logger.info(f"Schema created: {schema_name}")

            # 2. Update empresa record
            empresa.schema_name = schema_name
            empresa.schema_criado = True
            empresa.schema_criado_em = timezone.now()
            empresa.save(update_fields=[
                "schema_name",
                "schema_criado",
                "schema_criado_em"
            ])

            # 3. Register dynamic connection
            cls.register_connection(empresa)

            # 4. Apply migrations to new schema
            cls.migrate_schema(empresa)

            return schema_name

        except Exception as e:
            logger.error(f"Error creating schema {schema_name}: {e}")
            raise SchemaManagerError(f"Failed to create schema: {e}") from e

    @classmethod
    def register_connection(cls, empresa: "Empresa") -> str:
        """
        Dynamically register database connection for tenant schema.

        Returns:
            Alias of registered connection
        """
        if not empresa.schema_name:
            raise SchemaManagerError("Empresa does not have schema_name defined")

        db_alias = f"tenant_{empresa.schema_name}"

        if db_alias in connections.databases:
            return db_alias

        # Copy configuration from default
        default_db = settings.DATABASES["default"].copy()

        # Configure search_path for tenant schema
        options = default_db.get("OPTIONS", {}).copy()
        options["options"] = f"-c search_path={empresa.schema_name},public"
        default_db["OPTIONS"] = options

        # Register new connection
        connections.databases[db_alias] = default_db

        logger.info(f"Connection registered: {db_alias}")
        return db_alias

    @classmethod
    def migrate_schema(cls, empresa: "Empresa") -> None:
        """
        Apply migrations to tenant schema.
        """
        if not empresa.schema_criado:
            raise SchemaManagerError("Schema has not been created yet")

        db_alias = f"tenant_{empresa.schema_name}"

        # Ensure connection is registered
        cls.register_connection(empresa)

        for app in cls.TENANT_APPS:
            try:
                call_command(
                    "migrate",
                    app,
                    database=db_alias,
                    interactive=False,
                    verbosity=1,
                )
                logger.info(f"Migration applied: {app} on {db_alias}")
            except Exception as e:
                logger.error(f"Error migrating {app}: {e}")
                raise SchemaManagerError(
                    f"Failed to migrate {app}: {e}"
                ) from e

    @classmethod
    def delete_schema(cls, empresa: "Empresa", confirm: bool = False) -> None:
        """
        Remove schema from PostgreSQL.

        WARNING: This operation is IRREVERSIBLE and removes ALL data!

        Args:
            empresa: Empresa whose schema will be removed
            confirm: Must be True to confirm the operation
        """
        if not confirm:
            raise SchemaManagerError(
                "Destructive operation! Pass confirm=True to confirm."
            )

        if not empresa.schema_criado:
            return

        schema_name = empresa.schema_name

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT format('DROP SCHEMA IF EXISTS %I CASCADE', %s)",
                [schema_name]
            )
            drop_sql = cursor.fetchone()[0]
            cursor.execute(drop_sql)

        empresa.schema_criado = False
        empresa.schema_criado_em = None
        empresa.save(update_fields=["schema_criado", "schema_criado_em"])

        # Remove connection from pool
        db_alias = f"tenant_{schema_name}"
        if db_alias in connections.databases:
            del connections.databases[db_alias]

        logger.warning(f"Schema removed: {schema_name}")

    @classmethod
    def load_all_tenant_connections(cls) -> int:
        """
        Load all connections for dedicated tenants.
        Should be called at application startup.

        Returns:
            Number of connections loaded
        """
        from plataforma_de_servicos.empresa.models import Empresa
        from plataforma_de_servicos.empresa.models import TipoIsolamento

        count = 0
        try:
            empresas = Empresa.objects.filter(
                tipo_isolamento=TipoIsolamento.DEDICADO,
                schema_criado=True,
            )

            for empresa in empresas:
                try:
                    cls.register_connection(empresa)
                    count += 1
                except Exception as e:
                    logger.error(
                        f"Error loading connection for {empresa.slug}: {e}"
                    )
        except Exception as e:
            # May fail during initial migrations
            logger.debug(f"Could not load tenant connections: {e}")

        return count
