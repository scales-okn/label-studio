# Generated by Django 3.1.12 on 2021-08-29 14:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0020_auto_20210829_1450'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectgroup',
            name='template',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='projects.project'),
            preserve_default=False,
        ),
    ]