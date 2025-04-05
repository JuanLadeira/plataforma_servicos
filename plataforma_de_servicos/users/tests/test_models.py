import pytest
from plataforma_de_servicos.users.models import User

@pytest.mark.django_db
def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.pk}/"
