# Generated by Django 2.2.3 on 2019-07-20 04:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_auto_20190718_1655'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='log',
            name='key_name',
        ),
    ]
