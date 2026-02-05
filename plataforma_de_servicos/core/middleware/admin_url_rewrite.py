"""
Middleware para reescrever URLs do admin customizado da empresa.

Permite que cada empresa tenha seu próprio endpoint de admin (ex: /painel/, /admin-loja/, etc.)
que é internamente redirecionado para o gerente_site (/gerentes/).
"""


class AdminUrlRewriteMiddleware:
    """
    Reescreve URLs do admin customizado da empresa para /gerentes/.

    Exemplo:
    - Empresa com admin_url="painel"
    - Requisição para /painel/produto/
    - É reescrita internamente para /gerentes/produto/
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)

        # Se não tem tenant ou é o domínio principal, não faz nada
        if not tenant or getattr(request, "is_main_domain", False):
            return self.get_response(request)

        # Se a empresa tem um admin_url customizado diferente de "gerentes"
        admin_url = getattr(tenant, "admin_url", "gerentes")
        if admin_url and admin_url != "gerentes":
            custom_admin_path = f"/{admin_url}/"

            # Se o path começa com o admin customizado, reescreve para /gerentes/
            if request.path.startswith(custom_admin_path):
                # Guarda a URL original para uso em templates
                request.original_admin_url = custom_admin_path
                # Reescreve o path
                request.path = request.path.replace(custom_admin_path, "/gerentes/", 1)
                request.path_info = request.path

        return self.get_response(request)
