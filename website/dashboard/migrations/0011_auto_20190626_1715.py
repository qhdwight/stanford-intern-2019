# Generated by Django 2.2.2 on 2019-06-26 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_auto_20190626_1713'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='name',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
