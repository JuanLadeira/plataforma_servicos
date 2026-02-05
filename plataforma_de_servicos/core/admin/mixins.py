"""
Mixins para admin com suporte a multitenancy.
"""
from django import forms


class TenantAwareAdminMixin:
    """
    Mixin que filtra queryset por tenant e auto-preenche empresa.

    Aplica-se a ModelAdmin classes para modelos que têm campo 'empresa'.
    """

    def get_queryset(self, request):
        """Filtra queryset por tenant do request."""
        qs = super().get_queryset(request)

        # Superusuário sem tenant selecionado vê tudo
        if request.user.is_superuser and not request.tenant:
            return qs

        # Se o modelo tem campo empresa, filtra pelo tenant
        if hasattr(self.model, "empresa") and request.tenant:
            return qs.filter(empresa=request.tenant)

        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra FKs que apontam para modelos com empresa pelo tenant."""
        if request.tenant:
            related_model = db_field.remote_field.model
            if hasattr(related_model, "empresa"):
                kwargs["queryset"] = related_model.objects.filter(empresa=request.tenant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra M2M que apontam para modelos com empresa pelo tenant."""
        if request.tenant:
            related_model = db_field.remote_field.model
            if hasattr(related_model, "empresa"):
                kwargs["queryset"] = related_model.objects.filter(empresa=request.tenant)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Auto-preenche empresa ao criar novos objetos."""
        if not change and hasattr(obj, "empresa") and not obj.empresa_id:
            obj.empresa = request.tenant
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """Esconde campo empresa para usuários não-superusuários."""
        form = super().get_form(request, obj, **kwargs)
        if "empresa" in form.base_fields and not request.user.is_superuser:
            form.base_fields["empresa"].widget = forms.HiddenInput()
            form.base_fields["empresa"].initial = request.tenant
        return form


class TenantAwareInlineMixin:
    """
    Mixin para inlines com filtro por tenant.

    Aplica-se a TabularInline/StackedInline classes para modelos que têm
    relação com empresa (direta ou via parent).
    """

    def get_queryset(self, request):
        """Filtra queryset por tenant do request."""
        qs = super().get_queryset(request)
        if hasattr(self.model, "empresa") and request.tenant:
            return qs.filter(empresa=request.tenant)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra FKs que apontam para modelos com empresa pelo tenant."""
        if request.tenant:
            related_model = db_field.remote_field.model
            if hasattr(related_model, "empresa"):
                kwargs["queryset"] = related_model.objects.filter(empresa=request.tenant)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra M2M que apontam para modelos com empresa pelo tenant."""
        if request.tenant:
            related_model = db_field.remote_field.model
            if hasattr(related_model, "empresa"):
                kwargs["queryset"] = related_model.objects.filter(empresa=request.tenant)
        return super().formfield_for_manytomany(db_field, request, **kwargs)
