"""
Middleware para reescrever URLs dos portais administrativos customizados.

Permite que cada empresa tenha seus próprios endpoints de admin:
- Portal de Gerentes: ex: /painel/, /admin-loja/, etc. → /gerentes/
- Portal de Vendedores: ex: /equipe/, /meus-clientes/, etc. → /vendedores/

Isso aumenta a segurança, pois atacantes não sabem quais URLs tentar.
"""


class AdminUrlRewriteMiddleware:
    """
    Reescreve URLs customizadas dos portais para as URLs padrão.

    Exemplos:
    - Empresa com admin_url="painel" → /painel/ vira /gerentes/
    - Empresa com vendedor_url="equipe" → /equipe/ vira /vendedores/

    O middleware guarda a URL original no request para que templates
    e redirects possam manter a URL customizada visível ao usuário.
    """

    # URLs padrão dos portais
    DEFAULT_GERENTE_URL = "gerentes"
    DEFAULT_VENDEDOR_URL = "vendedores"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)

        # Se não tem tenant ou é o domínio principal, não faz nada
        if not tenant or getattr(request, "is_main_domain", False):
            return self.get_response(request)

        # Tenta reescrever URL de gerentes
        rewritten = self._rewrite_gerente_url(request, tenant)

        # Se não reescreveu gerentes, tenta vendedores
        if not rewritten:
            self._rewrite_vendedor_url(request, tenant)

        return self.get_response(request)

    def _rewrite_gerente_url(self, request, tenant):
        """
        Reescreve URL customizada de gerentes para /gerentes/.

        Returns:
            bool: True se a URL foi reescrita, False caso contrário.
        """
        admin_url = getattr(tenant, "admin_url", self.DEFAULT_GERENTE_URL)

        # Se usa URL padrão, não precisa reescrever
        if not admin_url or admin_url == self.DEFAULT_GERENTE_URL:
            return False

        custom_path = f"/{admin_url}/"
        default_path = f"/{self.DEFAULT_GERENTE_URL}/"

        if request.path.startswith(custom_path):
            # Guarda informações originais para uso em templates
            request.original_admin_url = custom_path
            request.admin_portal_type = "gerente"
            request.custom_admin_url = admin_url

            # Reescreve o path
            request.path = request.path.replace(custom_path, default_path, 1)
            request.path_info = request.path
            return True

        return False

    def _rewrite_vendedor_url(self, request, tenant):
        """
        Reescreve URL customizada de vendedores para /vendedores/.

        Returns:
            bool: True se a URL foi reescrita, False caso contrário.
        """
        vendedor_url = getattr(tenant, "vendedor_url", self.DEFAULT_VENDEDOR_URL)

        # Se usa URL padrão, não precisa reescrever
        if not vendedor_url or vendedor_url == self.DEFAULT_VENDEDOR_URL:
            return False

        custom_path = f"/{vendedor_url}/"
        default_path = f"/{self.DEFAULT_VENDEDOR_URL}/"

        if request.path.startswith(custom_path):
            # Guarda informações originais para uso em templates
            request.original_admin_url = custom_path
            request.admin_portal_type = "vendedor"
            request.custom_vendedor_url = vendedor_url

            # Reescreve o path
            request.path = request.path.replace(custom_path, default_path, 1)
            request.path_info = request.path
            return True

        return False
