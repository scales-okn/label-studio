# Generated by Django 3.1.12 on 2021-08-19 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_projectuser'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=300)),
                ('parents', models.ManyToManyField(to='projects.ProjectGroup')),
                ('projects', models.ManyToManyField(to='projects.Project')),
            ],
        ),
    ]