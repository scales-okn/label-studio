# Generated by Django 3.1.12 on 2021-08-25 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0016_auto_20210819_1828'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectSample',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
            ],
        ),
    ]
