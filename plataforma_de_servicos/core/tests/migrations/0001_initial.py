
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresa', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('empresa', models.ForeignKey(to='empresa.Empresa', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'app_label': 'core_tests',
            },
        ),
        migrations.CreateModel(
            name='NonTenantModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
            ],
            options={
                'app_label': 'core_tests',
            },
        ),
        migrations.CreateModel(
            name='RelatedModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('empresa', models.ForeignKey(to='empresa.Empresa', on_delete=django.db.models.deletion.CASCADE)),
                ('tenant_model', models.ForeignKey(to='core_tests.TenantModel', on_delete=django.db.models.deletion.CASCADE)),
            ],
            options={
                'app_label': 'core_tests',
            },
        ),
    ]
