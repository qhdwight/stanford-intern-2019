# Generated by Django 2.2.3 on 2019-07-09 19:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_experimentitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExperimentLogPk',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('log_pk', models.PositiveIntegerField()),
            ],
        ),
    ]
