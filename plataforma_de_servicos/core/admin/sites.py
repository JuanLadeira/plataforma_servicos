from unfold.sites import UnfoldAdminSite

class GerenteAdminSite(UnfoldAdminSite):
    site_header = "Portal dos Gerentes"
    site_title = "Gestão de Produtos e Serviços"
    index_title = "Administração dos Gerentes"
    
    def has_permission(self, request):
        """
        Verifica se o usuário tem permissão para acessar o site
        """
        if not request.user.is_authenticated:
            return False
        return request.user.is_active and (request.user.is_staff or request.user.is_superuser)

    def each_context(self, request):
        context = super().each_context(request)
        context['site_url'] = '/gerentes'
        return context


gerente_site = GerenteAdminSite(name='gerentes')