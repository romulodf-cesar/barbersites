# Generated by Django 4.1 on 2025-07-15 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='plano',
            options={'verbose_name': 'Plano', 'verbose_name_plural': 'Planos'},
        ),
        migrations.AlterField(
            model_name='plano',
            name='descricao',
            field=models.TextField(blank=True, null=True, verbose_name='Descrição'),
        ),
    ]
