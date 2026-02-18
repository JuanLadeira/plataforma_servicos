# Add unique constraint after data is populated

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('corretor', '0008_populate_interesse_numeros'),
        ('empresa', '0004_add_admin_ui_customization'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='interessecompra',
            unique_together={('empresa', 'numero')},
        ),
    ]
