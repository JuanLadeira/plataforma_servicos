from collections.abc import Sequence
from typing import Any

from factory import Faker, SubFactory
from factory import post_generation
from factory.django import DjangoModelFactory

from plataforma_de_servicos.empresa.tests.factories.empresa_factory import EmpresaFactory
from plataforma_de_servicos.users.models import Funcionario, User, UserType


class UserFactory(DjangoModelFactory[User]):
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):  # noqa: FBT001
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = User
        django_get_or_create = ["email"]


class FuncionarioUserFactory(UserFactory):
    """
    Uma UserFactory que define o user_type como FUNCIONARIO.
    """

    class Meta:
        model = User
        django_get_or_create = ["email"]

    user_type = UserType.FUNCIONARIO


class FuncionarioFactory(DjangoModelFactory):
    """
    Factory para o modelo Funcionario, que também cria um User associado.
    """

    class Meta:
        model = Funcionario

    usuario = SubFactory(FuncionarioUserFactory)
    empresa = SubFactory(EmpresaFactory)
    cargo = Faker("job")
    endereco = Faker("address")
    cpf = Faker("cpf", locale="pt_BR")