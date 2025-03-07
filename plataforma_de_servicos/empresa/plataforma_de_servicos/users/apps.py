import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "plataforma_de_servicos.users"
    verbose_name = _("Users")

    def ready(self):
        with contextlib.suppress(ImportError):
            import plataforma_de_servicos.users.signals  # noqa: F401
