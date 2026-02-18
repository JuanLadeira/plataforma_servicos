"""
Database utilities for multi-tenancy with dedicated database support.

This module provides:
- context: Thread-local/context-var storage for current tenant
- router: Database router for directing queries to correct schema
"""

from .context import clear_current_tenant
from .context import get_current_tenant
from .context import set_current_tenant
from .router import TenantDatabaseRouter

__all__ = [
    "get_current_tenant",
    "set_current_tenant",
    "clear_current_tenant",
    "TenantDatabaseRouter",
]
