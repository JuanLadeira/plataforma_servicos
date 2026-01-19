# Manual migration to fix Order model fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0003_auto_20260117_1851'),
    ]

    operations = [
        # Remove fields that don't exist in the current model
        migrations.RemoveField(
            model_name='order',
            name='products_ordered',
        ),
        migrations.RemoveField(
            model_name='order',
            name='total_quantity',
        ),
        # Rename total_cost to amount_paid to match current model
        migrations.RenameField(
            model_name='order',
            old_name='total_cost',
            new_name='amount_paid',
        ),
    ]