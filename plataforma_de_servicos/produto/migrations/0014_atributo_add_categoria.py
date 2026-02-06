# Generated manually for atributo category migration

from django.db import migrations, models
import django.db.models.deletion


def migrate_atributos_to_categoria(apps, schema_editor):
    """
    Migra atributos existentes para suas respectivas categorias.

    Lógica:
    - Para cada atributo, encontra produtos que usam suas variações
    - Associa o atributo à categoria do primeiro produto encontrado
    - Se não encontrar produto, associa à primeira categoria da empresa
    """
    Atributo = apps.get_model('produto', 'Atributo')
    Categoria = apps.get_model('produto', 'Categoria')
    VariacaoProduto = apps.get_model('produto', 'VariacaoProduto')

    for atributo in Atributo.objects.filter(categoria__isnull=True):
        categoria = None

        # Tenta encontrar uma categoria via produtos que usam este atributo
        variacoes = VariacaoProduto.objects.filter(
            valores__atributo=atributo
        ).select_related('produto__categoria').first()

        if variacoes and variacoes.produto.categoria:
            categoria = variacoes.produto.categoria
        else:
            # Fallback: primeira categoria da empresa
            if atributo.empresa_id:
                categoria = Categoria.objects.filter(
                    empresa_id=atributo.empresa_id
                ).first()
            else:
                # Se não tem empresa, pega a primeira categoria disponível
                categoria = Categoria.objects.first()

        if categoria:
            atributo.categoria = categoria
            atributo.save(update_fields=['categoria'])
            print(f"  Atributo '{atributo.nome}' -> Categoria '{categoria.categoria}'")
        else:
            print(f"  AVISO: Atributo '{atributo.nome}' sem categoria disponível!")


def reverse_migration(apps, schema_editor):
    """Reverse: copia empresa da categoria de volta para o atributo."""
    Atributo = apps.get_model('produto', 'Atributo')

    for atributo in Atributo.objects.filter(categoria__isnull=False):
        if atributo.categoria and atributo.categoria.empresa:
            atributo.empresa = atributo.categoria.empresa
            atributo.save(update_fields=['empresa'])


class Migration(migrations.Migration):

    dependencies = [
        ('produto', '0013_atributo_empresa_categoria_empresa_produto_empresa_and_more'),
    ]

    operations = [
        # 1. Adiciona campo categoria (nullable inicialmente)
        migrations.AddField(
            model_name='atributo',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='atributos',
                to='produto.categoria',
                verbose_name='Categoria',
                help_text='Categoria à qual este atributo pertence',
            ),
        ),

        # 2. Migra dados existentes
        migrations.RunPython(migrate_atributos_to_categoria, reverse_migration),

        # 3. Remove constraint antiga
        migrations.RemoveConstraint(
            model_name='atributo',
            name='unique_empresa_atributo_slug',
        ),

        # 4. Remove unique_together antigo
        migrations.AlterUniqueTogether(
            name='atributo',
            unique_together=set(),
        ),

        # 5. Remove campo empresa
        migrations.RemoveField(
            model_name='atributo',
            name='empresa',
        ),

        # 6. Torna categoria obrigatório
        migrations.AlterField(
            model_name='atributo',
            name='categoria',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='atributos',
                to='produto.categoria',
                verbose_name='Categoria',
                help_text='Categoria à qual este atributo pertence',
            ),
        ),

        # 7. Adiciona novo unique_together
        migrations.AlterUniqueTogether(
            name='atributo',
            unique_together={('categoria', 'nome')},
        ),

        # 8. Adiciona nova constraint
        migrations.AddConstraint(
            model_name='atributo',
            constraint=models.UniqueConstraint(
                fields=['categoria', 'slug'],
                name='unique_categoria_atributo_slug',
            ),
        ),

        # 9. Atualiza ordering
        migrations.AlterModelOptions(
            name='atributo',
            options={
                'ordering': ['categoria', 'nome'],
                'verbose_name': 'Atributo',
                'verbose_name_plural': 'Atributos',
            },
        ),
    ]
