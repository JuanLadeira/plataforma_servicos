
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import TextChoices
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class UserType(TextChoices):
    FUNCIONARIO = "FUNCIONARIO", _("Funcionario")
    CLIENTE = "CLIENTE", _("Cliente")


class User(AbstractUser):
    user_type = CharField(
        _("User Type"),
        max_length=50,
        choices=UserType.choices,
        default=UserType.CLIENTE,
    )
    """
    Default custom user model for plataforma_de_servicos.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    @property
    def is_cliente(self):
        return self.user_type == UserType.CLIENTE.value

    @property
    def is_funcionario(self):
        return self.user_type == UserType.FUNCIONARIO.value


class Funcionario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    cargo = models.CharField(max_length=100)
    endereco = models.CharField(max_length=255)
    cpf = models.CharField(
        max_length=14,
        unique=True,
        help_text="CPF único no formato 'XXX.XXX.XXX-XX'")
    is_signatario = models.BooleanField(default=False)

    def __str__(self):
        return super().__str__()


class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    empresa = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE)

    def __str__(self):
        return super().__str__()


    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    email = models.EmailField()

    def __str__(self):
        return super().__str__()
