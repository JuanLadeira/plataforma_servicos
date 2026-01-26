from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0003_alter_inventariosaldo_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventario',
            name='exibir_na_vitrine',
            field=models.BooleanField(
                default=False,
                help_text='Se marcado, os produtos deste inventário serão exibidos na página inicial para os clientes.',
                verbose_name='Exibir na Vitrine',
            ),
        ),
    ]
