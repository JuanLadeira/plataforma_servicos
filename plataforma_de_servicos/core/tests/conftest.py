
import pytest
from plataforma_de_servicos.empresa.models import Empresa

def pytest_configure():
    from django.conf import settings

    settings.INSTALLED_APPS += [
        'plataforma_de_servicos.core.tests.apps.CoreTestsAppConfig',
    ]

@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(nome="Empresa A", slug="empresa-a")

@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(nome="Empresa B", slug="empresa-b")
