"""
Middleware para identificar o tenant (empresa) baseado no subdomínio ou usuário autenticado.
"""
from django.http import Http404

from plataforma_de_servicos.empresa.models import Empresa


class TenantMiddleware:
    """
    Extrai tenant do subdomínio e injeta no request.

    Lógica:
    - /admin/: Apenas acessível no domínio principal (sem subdomínio)
    - URLs públicas em subdomínio: tenant vem do subdomínio (empresa-slug.dominio.com)
    - Admin da empresa: Endpoint customizável via campo admin_url (padrão: /gerentes/)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.is_main_domain = False

        if self._is_static_request(request.path):
            return self.get_response(request)

        # Determina se estamos no domínio principal (sem subdomínio)
        is_main_domain = self._is_main_domain(request)
        request.is_main_domain = is_main_domain

        # /admin/ só é acessível no domínio principal
        if request.path.startswith("/admin/"):
            if not is_main_domain:
                raise Http404("Página não encontrada")
            # No admin principal, não definimos tenant
            return self.get_response(request)

        # Se estamos em um subdomínio, identificar o tenant
        if not is_main_domain:
            tenant = self._get_tenant_from_subdomain(request)
            request.tenant = tenant

            if tenant:
                # Verifica se o caminho é o admin customizado da empresa
                admin_path = f"/{tenant.admin_url}/"
                if request.path.startswith(admin_path) or request.path.startswith("/gerentes/"):
                    # Admin da empresa: valida usuário
                    request.tenant = self._get_tenant_from_user(request) or tenant
            return self.get_response(request)

        # Domínio principal sem subdomínio (localhost/desenvolvimento)
        # Suporta tenant via query param ou sessão para facilitar testes

        # Para /gerentes/, tenta obter do usuário primeiro
        if request.path.startswith("/gerentes/"):
            request.tenant = self._get_tenant_from_user(request)
            if not request.tenant:
                request.tenant = self._get_dev_tenant(request)
        else:
            # Para outras URLs públicas, também suporta dev tenant
            request.tenant = self._get_dev_tenant(request)

        return self.get_response(request)

    def _is_main_domain(self, request):
        """Verifica se a requisição é do domínio principal (sem subdomínio)."""
        host = request.get_host().split(":")[0]  # Remove porta

        # Localhost/127.0.0.1 sem subdomínio é considerado domínio principal
        if host in ("localhost", "127.0.0.1"):
            return True

        # Verifica se tem subdomínio
        parts = host.split(".")

        # Suporte a subdomínios de localhost (ex: autoprime.localhost)
        if len(parts) == 2 and parts[1] == "localhost":
            return False  # É um subdomínio de localhost

        # Suporte a lvh.me para desenvolvimento (ex: autoprime.lvh.me)
        if len(parts) == 3 and parts[1] == "lvh" and parts[2] == "me":
            return False  # É um subdomínio de lvh.me

        # dominio.com (2 partes) = domínio principal
        # empresa.dominio.com (3+ partes) = subdomínio
        if len(parts) < 3:
            return True

        # Verifica se o primeiro segmento é "www" (não é um tenant)
        if parts[0] == "www":
            return True

        return False

    def _get_tenant_from_subdomain(self, request):
        """Extrai o tenant do subdomínio da requisição."""
        host = request.get_host().split(":")[0]
        parts = host.split(".")

        empresa_slug = None

        # Subdomínio de localhost (ex: autoprime.localhost)
        if len(parts) == 2 and parts[1] == "localhost":
            empresa_slug = parts[0]

        # Subdomínio de lvh.me (ex: autoprime.lvh.me)
        elif len(parts) == 3 and parts[1] == "lvh" and parts[2] == "me":
            empresa_slug = parts[0]

        # Subdomínio normal (ex: autoprime.dominio.com)
        elif len(parts) >= 3:
            empresa_slug = parts[0]

        if not empresa_slug or empresa_slug == "www":
            return None

        try:
            return Empresa.objects.get(slug=empresa_slug)
        except Empresa.DoesNotExist:
            return None

    def _get_tenant_from_user(self, request):
        """Obtém o tenant do usuário autenticado."""
        if not request.user.is_authenticated:
            return None

        # Funcionário: obtém empresa do perfil (tem prioridade)
        if hasattr(request.user, "funcionario") and request.user.funcionario:
            empresa = getattr(request.user.funcionario, "empresa", None)
            if empresa:
                return empresa

        # Superusuário pode selecionar tenant via sessão ou query param
        if request.user.is_superuser:
            # Tenta query param primeiro (para facilitar desenvolvimento)
            tenant_slug = request.GET.get("tenant")
            if tenant_slug:
                empresa = Empresa.objects.filter(slug=tenant_slug).first()
                if empresa:
                    # Salva na sessão para não precisar passar sempre
                    request.session["admin_tenant_id"] = empresa.pk
                    return empresa

            # Tenta sessão
            tenant_id = request.session.get("admin_tenant_id")
            if tenant_id:
                return Empresa.objects.filter(pk=tenant_id).first()

            return None

        # Cliente: obtém empresa do perfil
        if hasattr(request.user, "cliente") and request.user.cliente:
            return getattr(request.user.cliente, "empresa", None)

        return None

    def _get_dev_tenant(self, request):
        """Para desenvolvimento: obtém tenant via query param ou sessão."""
        empresa_slug = request.GET.get("tenant")
        if empresa_slug:
            request.session["dev_tenant_slug"] = empresa_slug
        else:
            empresa_slug = request.session.get("dev_tenant_slug")

        if empresa_slug:
            try:
                return Empresa.objects.get(slug=empresa_slug)
            except Empresa.DoesNotExist:
                return None
        return None

    def _is_static_request(self, path):
        """Verifica se é uma requisição de arquivo estático."""
        static_prefixes = ("/static/", "/media/", "/__debug__/", "/favicon.ico")
        return any(path.startswith(prefix) for prefix in static_prefixes)
