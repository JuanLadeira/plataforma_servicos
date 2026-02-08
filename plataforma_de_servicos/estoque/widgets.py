"""
Widgets customizados para o módulo de estoque.
"""
from django import forms


class VariacaoAutocompleteWidget(forms.Select):
    """
    Widget de autocomplete para variação que inclui estoque nos resultados.
    Usa select2 com AJAX apontando para nosso endpoint customizado.
    """

    class Media:
        css = {
            "all": (
                "admin/css/vendor/select2/select2.css",
                "admin/css/autocomplete.css",
            ),
        }
        js = (
            "admin/js/vendor/select2/select2.full.js",
        )

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)
        self.attrs.setdefault("class", "admin-autocomplete variacao-autocomplete")
        self.attrs["data-ajax--cache"] = "true"
        self.attrs["data-ajax--delay"] = "250"
        self.attrs["data-ajax--type"] = "GET"
        self.attrs["data-ajax--url"] = "/estoque/api/variacao-autocomplete/"
        self.attrs["data-theme"] = "admin-autocomplete"
        self.attrs["data-allow-clear"] = "true"
        self.attrs["data-placeholder"] = "Buscar variação..."

    def optgroups(self, name, value, attrs=None):
        """Gera opções para valores já selecionados."""
        from plataforma_de_servicos.produto.models import VariacaoProduto

        selected_choices = []
        for v in value:
            if v:
                try:
                    variacao = VariacaoProduto.objects.select_related("produto").prefetch_related("valores").get(pk=v)
                    valores = ", ".join(val.valor for val in variacao.valores.all())
                    text = f"{variacao.produto.produto} - {valores}" if valores else variacao.produto.produto
                    selected_choices.append((v, text))
                except VariacaoProduto.DoesNotExist:
                    pass

        self.choices = selected_choices
        return super().optgroups(name, value, attrs)
