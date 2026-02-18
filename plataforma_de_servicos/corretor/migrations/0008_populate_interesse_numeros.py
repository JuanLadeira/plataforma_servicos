# Data migration to populate numero field

from django.db import migrations
from django.utils import timezone


def populate_numeros(apps, schema_editor):
    """Popula números únicos para interesses existentes."""
    InteresseCompra = apps.get_model('corretor', 'InteresseCompra')

    # Group by empresa and assign numbers
    empresa_ids = InteresseCompra.objects.values_list('empresa_id', flat=True).distinct()
    ano = timezone.now().year

    for empresa_id in empresa_ids:
        if empresa_id:
            interesses = InteresseCompra.objects.filter(empresa_id=empresa_id).order_by('created')
            for i, interesse in enumerate(interesses, 1):
                interesse.numero = f'IC-{ano}-{i:05d}'
                interesse.save(update_fields=['numero'])
        else:
            # Handle ones without empresa
            for interesse in InteresseCompra.objects.filter(empresa__isnull=True):
                interesse.numero = f'IC-LEGACY-{interesse.pk:05d}'
                interesse.save(update_fields=['numero'])


def reverse_populate(apps, schema_editor):
    """Reverse: clear all numeros."""
    InteresseCompra = apps.get_model('corretor', 'InteresseCompra')
    InteresseCompra.objects.all().update(numero='')


class Migration(migrations.Migration):

    dependencies = [
        ('corretor', '0007_add_numero_to_interessecompra'),
    ]

    operations = [
        migrations.RunPython(populate_numeros, reverse_populate),
    ]
