
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import TextChoices
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from plataforma_de_servicos.empresa.models import Empresa

from .managers import UserManager


class UserType(TextChoices):
    FUNCIONARIO = "FUNCIONARIO", _("Funcionario")
    CLIENTE = "CLIENTE", _("Cliente")


class PapelFuncionario(TextChoices):
    VENDEDOR = "VENDEDOR", _("Vendedor")
    GERENTE = "GERENTE", _("Gerente")
    ADMIN = "ADMIN", _("Administrador")


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
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="users",
        verbose_name=_("Empresa"),
        null=True,
        blank=True,
        help_text=_("Empresa à qual o usuário pertence"),
    )

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
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="funcionarios",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )
    papel = models.CharField(
        "papel",
        max_length=20,
        choices=PapelFuncionario.choices,
        default=PapelFuncionario.VENDEDOR,
        help_text="Define o nível de acesso do funcionário no sistema",
    )
    cargo = models.CharField("cargo", max_length=100, blank=True)
    endereco = models.CharField("endereço", max_length=255, blank=True)
    cpf = models.CharField(
        "CPF",
        max_length=14,
        blank=True,
        help_text="CPF no formato 'XXX.XXX.XXX-XX'",
    )
    telefone = models.CharField("telefone", max_length=20, blank=True)
    is_corretor = models.BooleanField(
        "é corretor",
        default=False,
        help_text="Indica se o funcionário atua como corretor/vendedor",
    )
    is_signatario = models.BooleanField("é signatário", default=False)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "funcionário"
        verbose_name_plural = "funcionários"
        ordering = ["usuario__name"]

    def __str__(self):
        return self.usuario.name or self.usuario.email

    @property
    def nome(self):
        """Retorna o nome do usuário."""
        return self.usuario.name or self.usuario.email

    @property
    def email(self):
        """Retorna o email do usuário."""
        return self.usuario.email

    @property
    def is_vendedor(self):
        """Verifica se funcionário é vendedor ou superior."""
        return self.papel in [
            PapelFuncionario.VENDEDOR,
            PapelFuncionario.GERENTE,
            PapelFuncionario.ADMIN,
        ]

    @property
    def is_gerente(self):
        """Verifica se funcionário é gerente ou superior."""
        return self.papel in [
            PapelFuncionario.GERENTE,
            PapelFuncionario.ADMIN,
        ]

    @property
    def is_admin(self):
        """Verifica se funcionário é administrador."""
        return self.papel == PapelFuncionario.ADMIN


class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    def __str__(self):
        return super().__str__()
