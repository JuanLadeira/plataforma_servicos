from django import forms

from .models import InteresseCompra


class InteresseCompraForm(forms.ModelForm):
    """Formulário para demonstração de interesse."""

    class Meta:
        model = InteresseCompra
        fields = ["nome_cliente", "email_cliente", "telefone_cliente", "mensagem"]
        widgets = {
            "nome_cliente": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Seu nome completo",
                    "required": True,
                }
            ),
            "email_cliente": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "seu@email.com",
                    "required": True,
                }
            ),
            "telefone_cliente": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "(11) 99999-9999",
                    "required": True,
                }
            ),
            "mensagem": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Alguma observação ou dúvida? (opcional)",
                    "rows": 3,
                }
            ),
        }
        labels = {
            "nome_cliente": "Nome completo",
            "email_cliente": "E-mail",
            "telefone_cliente": "Telefone",
            "mensagem": "Mensagem (opcional)",
        }
