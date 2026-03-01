"""
User services - Serviços para gerenciamento de usuários e permissões.
"""
from plataforma_de_servicos.users.services.permission_service import Permission
from plataforma_de_servicos.users.services.permission_service import PermissionService
from plataforma_de_servicos.users.services.permission_service import PermissionServiceError
from plataforma_de_servicos.users.services.permission_service import ROLE_PERMISSIONS

__all__ = [
    "Permission",
    "PermissionService",
    "PermissionServiceError",
    "ROLE_PERMISSIONS",
]
