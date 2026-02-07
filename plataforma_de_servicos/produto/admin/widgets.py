"""
Widgets customizados para o admin de produtos.
"""
from itertools import groupby

from django import forms
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe


class GroupedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """
    Widget que renderiza checkboxes agrupados por atributo,
    estilizados como chips/tags clicáveis para melhor UX.

    Para atributos com multipla_selecao=False, usa radio buttons.
    Para atributos com multipla_selecao=True, usa checkboxes.
    """

    template_name = "admin/widgets/grouped_checkbox_select.html"

    def __init__(
        self,
        attrs=None,
        group_by_field="atributo",
        categoria_id=None,
        admin_site="gerentes",
        atributos_config=None,
    ):
        self.group_by_field = group_by_field
        self.categoria_id = categoria_id
        self.admin_site = admin_site
        # Dict: {nome_atributo: multipla_selecao}
        self.atributos_config = atributos_config or {}
        super().__init__(attrs)

    def optgroups(self, name, value, attrs=None):
        """Override to group options by atributo."""
        groups = []
        has_selected = False

        # Convert value to list of strings for comparison
        if value is None:
            value = []
        value = [str(v) for v in value]

        for index, (option_value, option_label) in enumerate(self.choices):
            selected = str(option_value) in value

            if selected:
                has_selected = True

            groups.append({
                "name": name,
                "value": option_value,
                "label": option_label,
                "selected": selected,
                "index": index,
                "attrs": self.build_attrs(attrs, {"id": f"{attrs.get('id', name)}_{index}"}),
            })

        return groups, has_selected

    def render(self, name, value, attrs=None, renderer=None):
        """Renderiza o widget com agrupamento visual por atributo."""
        if attrs is None:
            attrs = {}

        final_attrs = self.build_attrs(attrs, {"name": name})
        widget_id = final_attrs.get("id", name)

        # Obter as opções
        if value is None:
            value = []
        value = [str(v) for v in value]

        # Agrupar choices por atributo
        grouped_choices = {}
        for option_value, option_label in self.choices:
            # option_label é algo como "Cor: Vermelho"
            label_str = str(option_label)
            if ": " in label_str:
                atributo, valor = label_str.split(": ", 1)
            else:
                atributo = "Outros"
                valor = label_str

            if atributo not in grouped_choices:
                grouped_choices[atributo] = []

            grouped_choices[atributo].append({
                "value": option_value,
                "label": valor,
                "full_label": label_str,
                "selected": str(option_value) in value,
            })

        # Gerar URLs para adicionar atributo e valor
        add_links_html = self._render_add_links()

        # Renderizar HTML
        html_parts = ['<div class="valores-atributo-container">']

        if not grouped_choices:
            # Estado vazio - mostrar mensagem e links
            html_parts.append(
                '<div class="valores-empty-state">'
                '<span class="empty-message">Nenhum valor disponível para esta categoria.</span>'
                f'{add_links_html}'
                '</div>'
            )
        else:
            for atributo, valores in grouped_choices.items():
                # Verificar se permite múltipla seleção
                multipla_selecao = self.atributos_config.get(atributo, True)
                # Sempre usar checkbox para ManyToMany funcionar corretamente
                # O JavaScript cuida de simular radio (desmarcar outros) quando multipla_selecao=False
                selection_hint = "" if multipla_selecao else ' <span class="selection-hint">(escolha 1)</span>'

                html_parts.append(
                    f'<div class="atributo-group" data-multipla="{str(multipla_selecao).lower()}">'
                    f'<span class="atributo-label">{escape(atributo)}{selection_hint}</span>'
                    f'<div class="valores-chips">'
                )

                for idx, item in enumerate(valores):
                    input_id = f"{widget_id}_{item['value']}"
                    checked = "checked" if item["selected"] else ""

                    html_parts.append(
                        f'<label class="valor-chip {checked}" for="{input_id}">'
                        f'<input type="checkbox" name="{name}" value="{item["value"]}" '
                        f'id="{input_id}" {checked} class="valor-checkbox" '
                        f'data-atributo="{escape(atributo)}" data-multipla="{str(multipla_selecao).lower()}">'
                        f'<span class="chip-text">{escape(item["label"])}</span>'
                        f'</label>'
                    )

                html_parts.append("</div></div>")

            # Adicionar links no final
            html_parts.append(f'<div class="valores-add-links">{add_links_html}</div>')

        html_parts.append("</div>")

        return mark_safe("".join(html_parts))

    def _render_add_links(self):
        """Renderiza os links para adicionar novo atributo e valor."""
        links = []

        # Montar parâmetro de categoria
        categoria_param = f"?_categoria={self.categoria_id}" if self.categoria_id else ""

        try:
            # Link para adicionar novo atributo
            add_atributo_url = reverse(f"{self.admin_site}:produto_atributo_add")
            links.append(
                f'<a href="{add_atributo_url}{categoria_param}" '
                f'class="add-link add-atributo-link" target="_blank" '
                f'title="Criar novo atributo (ex: Cor, Tamanho)">'
                f'<span class="add-icon">+</span> Novo Atributo'
                f'</a>'
            )
        except Exception:
            pass

        try:
            # Link para adicionar novo valor de atributo
            add_valor_url = reverse(f"{self.admin_site}:produto_valoratributo_add")
            links.append(
                f'<a href="{add_valor_url}{categoria_param}" '
                f'class="add-link add-valor-link" target="_blank" '
                f'title="Criar novo valor para um atributo existente">'
                f'<span class="add-icon">+</span> Novo Valor'
                f'</a>'
            )
        except Exception:
            pass

        return " ".join(links)

    class Media:
        css = {
            "all": ("css/valores-atributo-widget.css",)
        }
        js = ("js/valores-atributo-widget.js",)
