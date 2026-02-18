"""
Base class for Celery tasks with tenant context.
"""
from celery import Task

from plataforma_de_servicos.core.db.context import clear_current_tenant
from plataforma_de_servicos.core.db.context import set_current_tenant


class TenantTask(Task):
    """
    Task base that sets up tenant context before execution.

    Usage:
        @app.task(base=TenantTask, bind=True)
        def my_task(self, empresa_id, ...):
            # Tenant context is already set up
            # Queries to tenant models will be routed correctly
            ...

    The first argument MUST be empresa_id.
    """

    def __call__(self, empresa_id, *args, **kwargs):
        from plataforma_de_servicos.empresa.models import Empresa

        tenant = None
        try:
            tenant = Empresa.objects.get(pk=empresa_id)
            set_current_tenant(tenant)
        except Empresa.DoesNotExist:
            pass

        try:
            return super().__call__(empresa_id, *args, **kwargs)
        finally:
            clear_current_tenant()
