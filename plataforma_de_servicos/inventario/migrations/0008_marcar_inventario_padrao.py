from django.db import migrations

from plataforma_de_servicos.inventario.migrations_utils import marcar_padroes


def forwards(apps, schema_editor):
    marcar_padroes(apps.get_model("inventario", "Inventario"))


class Migration(migrations.Migration):
    dependencies = [("inventario", "0007_inventario_padrao")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
