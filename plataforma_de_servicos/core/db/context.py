"""
Thread-local/context-var storage for current tenant.

Used by TenantDatabaseRouter to determine which database to use.

ContextVar is preferred over threading.local for async compatibility.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING
from typing import Optional

if TYPE_CHECKING:
    from plataforma_de_servicos.empresa.models import Empresa

# ContextVar for storing current tenant in async-safe manner
_current_tenant: ContextVar[Optional["Empresa"]] = ContextVar(
    "current_tenant", default=None
)


def set_current_tenant(tenant: Optional["Empresa"]) -> None:
    """
    Set the current tenant for this context.

    Should be called by TenantMiddleware at the start of each request.

    Args:
        tenant: The Empresa instance to set as current tenant, or None.
    """
    _current_tenant.set(tenant)


def get_current_tenant() -> Optional["Empresa"]:
    """
    Get the current tenant for this context.

    Returns:
        The current Empresa instance, or None if not set.
    """
    return _current_tenant.get()


def clear_current_tenant() -> None:
    """
    Clear the current tenant from this context.

    Should be called by TenantMiddleware after processing each request.
    """
    _current_tenant.set(None)
