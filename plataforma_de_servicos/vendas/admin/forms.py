from django import forms
from django.utils.translation import gettext_lazy as _

from unfold.widgets import UnfoldAdminTextareaWidget


class RejeicaoOrdemForm(forms.Form):
    """Formulario para coletar motivo da rejeicao da ordem."""

    motivo = forms.CharField(
        label=_("Motivo da rejeicao"),
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 4}),
        required=True,
        help_text=_("Informe o motivo pelo qual a ordem esta sendo rejeitada."),
    )


class CancelamentoOrdemForm(forms.Form):
    """Formulario para coletar motivo do cancelamento da ordem."""

    motivo = forms.CharField(
        label=_("Motivo do cancelamento"),
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 4}),
        required=False,
        help_text=_("Informe o motivo do cancelamento (opcional)."),
    )
