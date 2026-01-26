from unfold.sites import UnfoldAdminSite

from plataforma_de_servicos.corretor.admin.gerente_admin import CorretorGerenteAdmin
from plataforma_de_servicos.corretor.admin.gerente_admin import InteresseCompraGerenteAdmin
from plataforma_de_servicos.corretor.models import Corretor
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueEntradaAdmin
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueSaidaAdmin
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
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
        Verifica se o usuário tem permissão para acessar o site
        """
        if not request.user.is_authenticated:
            return False
        return request.user.is_active and (request.user.is_staff or request.user.is_superuser)

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
gerente_site.register(Inventario, InventarioGerenteAdmin)
gerente_site.register(Corretor, CorretorGerenteAdmin)
gerente_site.register(InteresseCompra, InteresseCompraGerenteAdmin)
gerente_site.register(OrdemCompra, OrdemCompraGerenteAdmin)
