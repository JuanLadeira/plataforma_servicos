import pytest
from plataforma_de_servicos.users.models import User

pytestmark = [pytest.mark.django_db, pytest.mark.users]


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.pk}/"
