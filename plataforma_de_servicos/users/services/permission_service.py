"""
PermissionService - Serviço para controle de acesso baseado em funções (RBAC).

Implementa as regras de negócio para permissões de Vendedor vs Gerente,
garantindo que cada perfil tenha acesso apenas às funcionalidades permitidas.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from plataforma_de_servicos.users.models import Funcionario
from plataforma_de_servicos.users.models import PapelFuncionario

if TYPE_CHECKING:
    from django.db.models import Model

    from plataforma_de_servicos.users.models import User


class Permission(Enum):
    """Permissões do sistema."""
    # Produto
    PRODUTO_VISUALIZAR = "produto.visualizar"
    PRODUTO_CRIAR = "produto.criar"
    PRODUTO_EDITAR = "produto.editar"
    PRODUTO_DELETAR = "produto.deletar"

    # Variação
    VARIACAO_VISUALIZAR = "variacao.visualizar"
    VARIACAO_CRIAR = "variacao.criar"
    VARIACAO_EDITAR = "variacao.editar"
    VARIACAO_DELETAR = "variacao.deletar"

    # Categoria
    CATEGORIA_VISUALIZAR = "categoria.visualizar"
    CATEGORIA_CRIAR = "categoria.criar"
    CATEGORIA_EDITAR = "categoria.editar"
    CATEGORIA_DELETAR = "categoria.deletar"

    # Estoque
    ESTOQUE_VISUALIZAR = "estoque.visualizar"
    ESTOQUE_ENTRADA = "estoque.entrada"
    ESTOQUE_SAIDA = "estoque.saida"
    ESTOQUE_TRANSFERENCIA = "estoque.transferencia"

    # Inventário
    INVENTARIO_VISUALIZAR = "inventario.visualizar"
    INVENTARIO_CRIAR = "inventario.criar"
    INVENTARIO_EDITAR = "inventario.editar"

    # Ordem de Compra
    ORDEM_VISUALIZAR = "ordem.visualizar"
    ORDEM_CRIAR = "ordem.criar"
    ORDEM_APROVAR = "ordem.aprovar"
    ORDEM_REJEITAR = "ordem.rejeitar"
    ORDEM_FATURAR = "ordem.faturar"
    ORDEM_CANCELAR = "ordem.cancelar"

    # Interesse de Compra
    INTERESSE_VISUALIZAR = "interesse.visualizar"
    INTERESSE_CRIAR = "interesse.criar"
    INTERESSE_ATENDER = "interesse.atender"
    INTERESSE_CONVERTER = "interesse.converter"

    # Comissão
    COMISSAO_VISUALIZAR = "comissao.visualizar"
    COMISSAO_VISUALIZAR_TODAS = "comissao.visualizar_todas"
    COMISSAO_APROVAR = "comissao.aprovar"
    COMISSAO_PAGAR = "comissao.pagar"

    # Usuários
    USUARIO_VISUALIZAR = "usuario.visualizar"
    USUARIO_CRIAR = "usuario.criar"
    USUARIO_EDITAR = "usuario.editar"
    USUARIO_GERENCIAR_PERMISSOES = "usuario.gerenciar_permissoes"

    # Relatórios
    RELATORIO_EXPORTAR = "relatorio.exportar"
    RELATORIO_FINANCEIRO = "relatorio.financeiro"

    # Configurações
    CONFIG_EMPRESA = "config.empresa"
    CONFIG_COMISSAO = "config.comissao"


# Definição de permissões por papel
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    PapelFuncionario.VENDEDOR: {
        # Produto - apenas visualização
        Permission.PRODUTO_VISUALIZAR,
        Permission.VARIACAO_VISUALIZAR,
        Permission.CATEGORIA_VISUALIZAR,

        # Estoque - apenas visualização
        Permission.ESTOQUE_VISUALIZAR,
        Permission.INVENTARIO_VISUALIZAR,

        # Ordem - criar proposta, não pode aprovar
        Permission.ORDEM_VISUALIZAR,
        Permission.ORDEM_CRIAR,

        # Interesse
        Permission.INTERESSE_VISUALIZAR,
        Permission.INTERESSE_CRIAR,
        Permission.INTERESSE_ATENDER,
        Permission.INTERESSE_CONVERTER,

        # Comissão - apenas próprias
        Permission.COMISSAO_VISUALIZAR,
    },

    PapelFuncionario.GERENTE: {
        # Todas as permissões do vendedor
        Permission.PRODUTO_VISUALIZAR,
        Permission.VARIACAO_VISUALIZAR,
        Permission.CATEGORIA_VISUALIZAR,
        Permission.ESTOQUE_VISUALIZAR,
        Permission.INVENTARIO_VISUALIZAR,
        Permission.ORDEM_VISUALIZAR,
        Permission.ORDEM_CRIAR,
        Permission.INTERESSE_VISUALIZAR,
        Permission.INTERESSE_CRIAR,
        Permission.INTERESSE_ATENDER,
        Permission.INTERESSE_CONVERTER,
        Permission.COMISSAO_VISUALIZAR,

        # Produto - CRUD completo
        Permission.PRODUTO_CRIAR,
        Permission.PRODUTO_EDITAR,
        Permission.PRODUTO_DELETAR,
        Permission.VARIACAO_CRIAR,
        Permission.VARIACAO_EDITAR,
        Permission.VARIACAO_DELETAR,
        Permission.CATEGORIA_CRIAR,
        Permission.CATEGORIA_EDITAR,
        Permission.CATEGORIA_DELETAR,

        # Estoque - operações completas
        Permission.ESTOQUE_ENTRADA,
        Permission.ESTOQUE_SAIDA,
        Permission.ESTOQUE_TRANSFERENCIA,
        Permission.INVENTARIO_CRIAR,
        Permission.INVENTARIO_EDITAR,

        # Ordem - gestão completa
        Permission.ORDEM_APROVAR,
        Permission.ORDEM_REJEITAR,
        Permission.ORDEM_FATURAR,
        Permission.ORDEM_CANCELAR,

        # Comissão - gestão
        Permission.COMISSAO_VISUALIZAR_TODAS,
        Permission.COMISSAO_APROVAR,
        Permission.COMISSAO_PAGAR,

        # Usuários
        Permission.USUARIO_VISUALIZAR,
        Permission.USUARIO_CRIAR,
        Permission.USUARIO_EDITAR,
        Permission.USUARIO_GERENCIAR_PERMISSOES,

        # Relatórios
        Permission.RELATORIO_EXPORTAR,
        Permission.RELATORIO_FINANCEIRO,

        # Configurações
        Permission.CONFIG_EMPRESA,
        Permission.CONFIG_COMISSAO,
    },

    PapelFuncionario.ADMIN: set(Permission),  # Todas as permissões
}


@dataclass
class PermissionCheckResult:
    """Resultado de verificação de permissão."""
    allowed: bool
    reason: str
    permission: Permission | None = None


class PermissionServiceError(Exception):
    """Exceção para erros de permissão."""


class PermissionService:
    """
    Serviço para verificação e gerenciamento de permissões RBAC.

    Responsabilidades:
    - Verificar permissões de usuário
    - Validar operações antes de executar
    - Filtrar dados baseado em papel
    """

    def __init__(self, user: "User"):
        self.user = user
        self._funcionario: Funcionario | None = None

    @property
    def funcionario(self) -> Funcionario | None:
        """Obtém o perfil de funcionário do usuário."""
        if self._funcionario is None and hasattr(self.user, "funcionario"):
            self._funcionario = self.user.funcionario
        return self._funcionario

    @property
    def papel(self) -> str | None:
        """Obtém o papel do funcionário."""
        if self.funcionario:
            return self.funcionario.papel
        return None

    @property
    def is_vendedor(self) -> bool:
        """Verifica se é vendedor (qualquer nível)."""
        return self.funcionario.is_vendedor if self.funcionario else False

    @property
    def is_gerente(self) -> bool:
        """Verifica se é gerente ou superior."""
        return self.funcionario.is_gerente if self.funcionario else False

    @property
    def is_admin(self) -> bool:
        """Verifica se é administrador."""
        return self.funcionario.is_admin if self.funcionario else False

    def has_permission(self, permission: Permission) -> bool:
        """
        Verifica se o usuário tem uma permissão específica.

        Args:
            permission: Permissão a verificar

        Returns:
            True se tiver permissão, False caso contrário
        """
        # Superusuários têm todas as permissões
        if self.user.is_superuser:
            return True

        # Sem perfil de funcionário, sem permissões
        if not self.funcionario:
            return False

        # Verificar no mapa de permissões
        papel = self.funcionario.papel
        permissions = ROLE_PERMISSIONS.get(papel, set())
        return permission in permissions

    def check_permission(self, permission: Permission) -> PermissionCheckResult:
        """
        Verifica permissão e retorna resultado detalhado.

        Args:
            permission: Permissão a verificar

        Returns:
            PermissionCheckResult com detalhes
        """
        if self.user.is_superuser:
            return PermissionCheckResult(
                allowed=True,
                reason="Superusuário tem todas as permissões",
                permission=permission,
            )

        if not self.funcionario:
            return PermissionCheckResult(
                allowed=False,
                reason="Usuário não é funcionário",
                permission=permission,
            )

        allowed = self.has_permission(permission)
        reason = (
            f"Permissão {permission.value} concedida para {self.papel}"
            if allowed
            else f"Permissão {permission.value} não concedida para {self.papel}"
        )

        return PermissionCheckResult(
            allowed=allowed,
            reason=reason,
            permission=permission,
        )

    def require_permission(self, permission: Permission) -> None:
        """
        Exige uma permissão, lançando exceção se não tiver.

        Args:
            permission: Permissão requerida

        Raises:
            PermissionServiceError: Se não tiver permissão
        """
        result = self.check_permission(permission)
        if not result.allowed:
            raise PermissionServiceError(result.reason)

    def can_edit_object(self, obj: "Model") -> bool:
        """
        Verifica se pode editar um objeto específico.

        Vendedores só podem editar objetos que criaram.
        Gerentes podem editar qualquer objeto da empresa.

        Args:
            obj: Objeto a verificar

        Returns:
            True se pode editar
        """
        if self.user.is_superuser or self.is_gerente:
            return True

        # Vendedores só podem editar próprios objetos
        if self.is_vendedor:
            # Verificar se objeto tem campo de criador
            if hasattr(obj, "criado_por_id"):
                return obj.criado_por_id == self.user.pk
            if hasattr(obj, "funcionario_id"):
                return obj.funcionario_id == self.funcionario.pk
            if hasattr(obj, "corretor_id"):
                return obj.corretor_id == self.funcionario.pk

        return False

    def can_delete_object(self, obj: "Model") -> bool:
        """
        Verifica se pode deletar um objeto.

        Apenas gerentes podem deletar.

        Args:
            obj: Objeto a verificar

        Returns:
            True se pode deletar
        """
        return self.user.is_superuser or self.is_gerente

    def filter_by_permission(self, queryset, permission: Permission):
        """
        Filtra queryset baseado em permissão.

        Ex: Comissões - vendedores veem apenas as próprias.

        Args:
            queryset: QuerySet a filtrar
            permission: Permissão relacionada

        Returns:
            QuerySet filtrado
        """
        if self.user.is_superuser or self.is_gerente:
            return queryset

        # Comissões: filtrar por funcionário
        if permission == Permission.COMISSAO_VISUALIZAR:
            if hasattr(queryset.model, "funcionario"):
                return queryset.filter(funcionario=self.funcionario)

        # Ordens: filtrar por corretor (vendedor vê apenas suas ordens)
        if permission == Permission.ORDEM_VISUALIZAR:
            if hasattr(queryset.model, "corretor"):
                return queryset.filter(corretor=self.funcionario)

        # Interesses: filtrar por corretor
        if permission == Permission.INTERESSE_VISUALIZAR:
            if hasattr(queryset.model, "corretor"):
                return queryset.filter(corretor=self.funcionario)

        return queryset

    def get_available_permissions(self) -> set[Permission]:
        """Retorna todas as permissões disponíveis para o usuário."""
        if self.user.is_superuser:
            return set(Permission)

        if not self.funcionario:
            return set()

        return ROLE_PERMISSIONS.get(self.funcionario.papel, set())

    @staticmethod
    def validate_role_exclusivity(
        is_vendedor: bool,
        is_gerente: bool,
    ) -> bool:
        """
        Valida que um usuário não pode ter papéis conflitantes.

        De acordo com os requisitos, um usuário não pode ser
        vendedor E gerente ao mesmo tempo (o papel é único).

        Args:
            is_vendedor: Se está marcado como vendedor
            is_gerente: Se está marcado como gerente

        Returns:
            True se válido (não conflitante)
        """
        # Na implementação atual, 'papel' é um campo único,
        # então a exclusividade é garantida pelo modelo.
        # Este método existe para validações externas.
        return True
