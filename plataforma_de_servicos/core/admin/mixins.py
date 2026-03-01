"""
Mixins para admin com suporte a multitenancy e RBAC.
"""
from django import forms

from plataforma_de_servicos.users.services.permission_service import Permission
from plataforma_de_servicos.users.services.permission_service import PermissionService


def _has_empresa_field(model):
    """
    Verifica se o modelo tem um campo 'empresa' real (não property).

    Isso é necessário porque alguns modelos (como Atributo) têm uma property
    'empresa' que retorna empresa via relacionamento, mas não é um campo
    de banco de dados que pode ser usado em filter().
    """
    try:
        field = model._meta.get_field("empresa")
        # Verifica se é um campo real (ForeignKey, etc.) e não uma property
        return hasattr(field, "remote_field")
    except Exception:
        return False


class TenantAwareAdminMixin:
    """
    Mixin que filtra queryset por tenant e auto-preenche empresa.

    Aplica-se a ModelAdmin classes para modelos que têm campo 'empresa'.

    Comportamento:
    - No admin de gerentes (self.admin_site.name == 'gerentes'):
      - SEMPRE filtra por tenant
      - SEMPRE esconde campo empresa
      - SEMPRE auto-preenche empresa ao criar
      - Se não houver tenant, retorna queryset vazio (segurança)
    - No admin principal (/admin/):
      - Superusuários veem tudo
      - Filtro opcional por tenant
    """

    def _is_gerente_admin(self):
        """Verifica se estamos no admin de gerentes."""
        return getattr(self.admin_site, "name", "") == "gerentes"

    def get_queryset(self, request):
        """Filtra queryset por tenant do request."""
        qs = super().get_queryset(request)
        tenant = getattr(request, "tenant", None)

        # Se estamos no admin de gerentes
        if self._is_gerente_admin():
            # Sem tenant = queryset vazio (segurança)
            if not tenant:
                return qs.none()
            # Com tenant = filtra por empresa (se campo existe)
            if _has_empresa_field(self.model):
                return qs.filter(empresa=tenant)
            return qs

        # Admin principal: superusuário sem tenant vê tudo
        if request.user.is_superuser and not tenant:
            return qs

        # Se o modelo tem campo empresa, filtra pelo tenant
        if _has_empresa_field(self.model) and tenant:
            return qs.filter(empresa=tenant)

        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra FKs que apontam para modelos com empresa pelo tenant."""
        tenant = getattr(request, "tenant", None)

        # No admin de gerentes, sempre filtra
        if self._is_gerente_admin() and tenant:
            related_model = db_field.remote_field.model
            if _has_empresa_field(related_model):
                kwargs["queryset"] = related_model.objects.filter(empresa=tenant)
        elif tenant:
            related_model = db_field.remote_field.model
            if _has_empresa_field(related_model):
                kwargs["queryset"] = related_model.objects.filter(empresa=tenant)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra M2M que apontam para modelos com empresa pelo tenant."""
        tenant = getattr(request, "tenant", None)

        if tenant:
            related_model = db_field.remote_field.model
            if _has_empresa_field(related_model):
                kwargs["queryset"] = related_model.objects.filter(empresa=tenant)

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-preenche empresa ao criar novos objetos."""
        tenant = getattr(request, "tenant", None)

        if not change and _has_empresa_field(type(obj)) and not obj.empresa_id:
            if tenant:
                obj.empresa = tenant

        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """Esconde campo empresa no admin de gerentes."""
        form = super().get_form(request, obj, **kwargs)
        tenant = getattr(request, "tenant", None)

        if "empresa" in form.base_fields:
            # No admin de gerentes: SEMPRE esconde e auto-preenche
            if self._is_gerente_admin():
                form.base_fields["empresa"].widget = forms.HiddenInput()
                form.base_fields["empresa"].initial = tenant
                form.base_fields["empresa"].required = False
            # No admin principal: esconde para não-superusuários
            elif not request.user.is_superuser and tenant:
                form.base_fields["empresa"].widget = forms.HiddenInput()
                form.base_fields["empresa"].initial = tenant

        return form

    def get_exclude(self, request, obj=None):
        """Exclui campo empresa do formulário no admin de gerentes."""
        exclude = list(super().get_exclude(request, obj) or [])

        # No admin de gerentes, excluímos empresa dos fieldsets visíveis
        # mas mantemos via get_form para auto-preenchimento
        return exclude


class TenantAwareInlineMixin:
    """
    Mixin para inlines com filtro por tenant.

    Aplica-se a TabularInline/StackedInline classes para modelos que têm
    relação com empresa (direta ou via parent).
    """

    def _is_gerente_admin(self):
        """Verifica se estamos no admin de gerentes."""
        if hasattr(self, "admin_site"):
            return getattr(self.admin_site, "name", "") == "gerentes"
        return False

    def get_queryset(self, request):
        """Filtra queryset por tenant do request."""
        qs = super().get_queryset(request)
        tenant = getattr(request, "tenant", None)

        if _has_empresa_field(self.model) and tenant:
            return qs.filter(empresa=tenant)

        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra FKs que apontam para modelos com empresa pelo tenant."""
        tenant = getattr(request, "tenant", None)

        if tenant:
            related_model = db_field.remote_field.model
            if _has_empresa_field(related_model):
                kwargs["queryset"] = related_model.objects.filter(empresa=tenant)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra M2M que apontam para modelos com empresa pelo tenant."""
        tenant = getattr(request, "tenant", None)

        if tenant:
            related_model = db_field.remote_field.model
            if _has_empresa_field(related_model):
                kwargs["queryset"] = related_model.objects.filter(empresa=tenant)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


class RBACAdminMixin:
    """
    Mixin para controle de acesso baseado em funções (RBAC).

    Aplica permissões granulares baseadas no papel do funcionário
    (Vendedor, Gerente, Admin) usando o PermissionService.

    Uso:
        class MeuModelAdmin(RBACAdminMixin, TenantAwareAdminMixin, ModelAdmin):
            permission_view = Permission.PRODUTO_VISUALIZAR
            permission_add = Permission.PRODUTO_CRIAR
            permission_change = Permission.PRODUTO_EDITAR
            permission_delete = Permission.PRODUTO_DELETAR
            vendedor_readonly_fields = ['preco_custo', 'margem']
    """

    # Permissões requeridas para cada ação
    permission_view: Permission | None = None
    permission_add: Permission | None = None
    permission_change: Permission | None = None
    permission_delete: Permission | None = None

    # Campos que devem ser readonly para vendedores
    vendedor_readonly_fields: list = []

    def _get_permission_service(self, request):
        """Obtém instância do PermissionService para o usuário."""
        if not hasattr(request, "_permission_service"):
            request._permission_service = PermissionService(request.user)
        return request._permission_service

    def has_view_permission(self, request, obj=None):
        """Verifica permissão de visualização."""
        if request.user.is_superuser:
            return True

        if self.permission_view:
            service = self._get_permission_service(request)
            if not service.has_permission(self.permission_view):
                return False

        return super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        """Verifica permissão de criação."""
        if request.user.is_superuser:
            return True

        if self.permission_add:
            service = self._get_permission_service(request)
            if not service.has_permission(self.permission_add):
                return False

        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """Verifica permissão de edição."""
        if request.user.is_superuser:
            return True

        if self.permission_change:
            service = self._get_permission_service(request)
            if not service.has_permission(self.permission_change):
                return False

            # Vendedores só podem editar objetos que criaram
            if obj and service.is_vendedor and not service.is_gerente:
                if not service.can_edit_object(obj):
                    return False

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Verifica permissão de exclusão."""
        if request.user.is_superuser:
            return True

        if self.permission_delete:
            service = self._get_permission_service(request)
            if not service.has_permission(self.permission_delete):
                return False

        return super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        """Filtra queryset por permissão se necessário."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        service = self._get_permission_service(request)

        # Aplicar filtro de permissão se houver
        if self.permission_view:
            qs = service.filter_by_permission(qs, self.permission_view)

        return qs

    def get_readonly_fields(self, request, obj=None):
        """Adiciona campos readonly para vendedores."""
        readonly = list(super().get_readonly_fields(request, obj) or [])

        if request.user.is_superuser:
            return readonly

        service = self._get_permission_service(request)

        # Vendedores têm campos extras como readonly
        if service.is_vendedor and not service.is_gerente:
            readonly.extend(
                f for f in self.vendedor_readonly_fields if f not in readonly
            )

        return readonly
