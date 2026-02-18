"""
Database Router for multi-tenancy with dedicated database support.

Logic:
1. Shared models → always 'default' database
2. Tenant models + empresa with dedicated DB → tenant's schema
3. Tenant models + empresa with shared DB → 'default' (filtered by FK)
"""

from typing import Optional
from typing import Type

from django.db.models import Model

from .context import get_current_tenant


# Apps that ALWAYS stay in the public schema (default database)
SHARED_APPS = {
    # Django core
    "auth",
    "contenttypes",
    "sessions",
    "admin",
    "sites",
    # Django extensions
    "django_celery_beat",
    "django_celery_results",
    # Allauth
    "account",
    "socialaccount",
    # Our shared apps
    "empresa",
    "users",
    "core",
}

# Apps whose models go to tenant schema (when dedicated)
TENANT_APPS = {
    "produto",
    "inventario",
    "estoque",
    "vendas",
    "corretor",
    "servico",
    "payment",
    "cart",
}


class TenantDatabaseRouter:
    """
    Database router that directs queries to the correct database based on tenant.

    For tenants with tipo_isolamento=DEDICADO and schema_criado=True,
    queries to TENANT_APPS models are routed to the tenant's schema.

    For all other cases, queries go to the 'default' database.
    """

    def _app_label(self, model: Type[Model]) -> str:
        """Get the app label for a model."""
        return model._meta.app_label

    def _is_shared_app(self, model: Type[Model]) -> bool:
        """Check if model belongs to a shared app."""
        return self._app_label(model) in SHARED_APPS

    def _get_tenant_db_alias(self) -> Optional[str]:
        """
        Get the database alias for the current tenant if applicable.

        Returns:
            The database alias (e.g., 'tenant_empresa_abc') if tenant
            uses dedicated database, otherwise None.
        """
        tenant = get_current_tenant()
        if not tenant:
            return None

        # Check if tenant uses dedicated database
        if hasattr(tenant, "usa_banco_dedicado") and tenant.usa_banco_dedicado:
            return tenant.database_alias

        return None

    def db_for_read(self, model: Type[Model], **hints) -> str:
        """
        Determine database for read operations.

        Args:
            model: The model class being queried.
            **hints: Additional hints (instance, etc.)

        Returns:
            Database alias to use for this read.
        """
        if self._is_shared_app(model):
            return "default"

        tenant_db = self._get_tenant_db_alias()
        return tenant_db or "default"

    def db_for_write(self, model: Type[Model], **hints) -> str:
        """
        Determine database for write operations.

        Args:
            model: The model class being written.
            **hints: Additional hints (instance, etc.)

        Returns:
            Database alias to use for this write.
        """
        if self._is_shared_app(model):
            return "default"

        tenant_db = self._get_tenant_db_alias()
        return tenant_db or "default"

    def allow_relation(self, obj1: Model, obj2: Model, **hints) -> bool:
        """
        Determine if a relation between two objects is allowed.

        Relations between shared and tenant models are allowed.
        Relations between models in the same tenant are allowed.

        Args:
            obj1: First model instance.
            obj2: Second model instance.
            **hints: Additional hints.

        Returns:
            True if relation is allowed, False otherwise.
        """
        # Shared models can relate to anything
        if self._is_shared_app(type(obj1)) or self._is_shared_app(type(obj2)):
            return True

        # Tenant models can relate to each other (within same tenant context)
        return True

    def allow_migrate(self, db: str, app_label: str, model_name: str = None, **hints) -> bool:
        """
        Determine if migration should run on a database.

        - 'default' database receives ALL migrations
        - 'tenant_*' databases only receive TENANT_APPS migrations

        Args:
            db: Database alias.
            app_label: App label being migrated.
            model_name: Model name being migrated (optional).
            **hints: Additional hints.

        Returns:
            True if migration should run, False otherwise.
        """
        if db == "default":
            # Default database receives all migrations
            return True

        if db.startswith("tenant_"):
            # Tenant databases only receive tenant app migrations
            return app_label in TENANT_APPS

        return False
