from unfold.sites import UnfoldAdminSite

from plataforma_de_servicos.core.admin.site_config_admin import SiteConfigGerenteAdmin
from plataforma_de_servicos.core.models import SiteConfig
from plataforma_de_servicos.corretor.admin.gerente_admin import CorretorGerenteAdmin
from plataforma_de_servicos.corretor.admin.gerente_admin import (
    InteresseCompraGerenteAdmin,
)
from plataforma_de_servicos.corretor.models import Corretor
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueEntradaAdmin
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueSaidaAdmin
from plataforma_de_servicos.estoque.admin.gerente_admin import TransferenciaAdmin
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.estoque.models.proxys.transferencia import Transferencia
from plataforma_de_servicos.inventario.admin.gerente_admin import InventarioGerenteAdmin
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.admin.gerente_admin import AtributoGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import CategoriaGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import ProdutoGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import ValorAtributoGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import VariacaoProdutoGerenteAdmin
from plataforma_de_servicos.produto.models.atributos import Atributo
from plataforma_de_servicos.produto.models.atributos import ValorAtributo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.vendas.admin import OrdemCompraGerenteAdmin
from plataforma_de_servicos.vendas.models import OrdemCompra


class GerenteAdminSite(UnfoldAdminSite):
    site_header = "Portal dos Gerentes"
    site_title = "Gestão de Produtos e Serviços"
    index_title = "Administração dos Gerentes"

    settings_name = "UNFOLD_GERENTE_ADMIN"

    def has_permission(self, request):
        """
        Verifica se o usuário tem permissão para acessar o site.
        - Superusuários sempre têm acesso
        - Funcionários precisam ter empresa associada
        """
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        if request.user.is_superuser:
            return True

        # Funcionário precisa ter empresa associada
        if hasattr(request.user, "funcionario") and request.user.funcionario:
            return request.user.funcionario.empresa is not None

        return False

    def each_context(self, request):
        context = super().each_context(request)
        context["site_url"] = "/gerentes"
        return context


gerente_site = GerenteAdminSite(name="gerentes")

gerente_site.register(Produto, ProdutoGerenteAdmin)
gerente_site.register(Categoria, CategoriaGerenteAdmin)
gerente_site.register(Atributo, AtributoGerenteAdmin)
gerente_site.register(ValorAtributo, ValorAtributoGerenteAdmin)
gerente_site.register(VariacaoProduto, VariacaoProdutoGerenteAdmin)
gerente_site.register(EstoqueEntrada, EstoqueEntradaAdmin)
gerente_site.register(EstoqueSaida, EstoqueSaidaAdmin)
gerente_site.register(Transferencia, TransferenciaAdmin)
gerente_site.register(Inventario, InventarioGerenteAdmin)
gerente_site.register(Corretor, CorretorGerenteAdmin)
gerente_site.register(InteresseCompra, InteresseCompraGerenteAdmin)
gerente_site.register(OrdemCompra, OrdemCompraGerenteAdmin)
gerente_site.register(SiteConfig, SiteConfigGerenteAdmin)
