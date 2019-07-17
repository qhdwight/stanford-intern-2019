# Generated by Django 2.2.3 on 2019-07-17 20:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0021_auto_20190715_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysislabitem',
            name='data_set',
            field=models.TextField(max_length=16),
        ),
        migrations.AlterField(
            model_name='analysislabitem',
            name='name',
            field=models.TextField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='award',
            name='name',
            field=models.TextField(max_length=16, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='award',
            name='pi',
            field=models.TextField(max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='award',
            name='project',
            field=models.TextField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='award',
            name='rfa',
            field=models.TextField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='award',
            name='status',
            field=models.TextField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='assay_term_name',
            field=models.TextField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='assay_title',
            field=models.TextField(db_index=True, max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='experiment',
            name='name',
            field=models.TextField(max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='ipaddress',
            name='city',
            field=models.TextField(max_length=32),
        ),
        migrations.AlterField(
            model_name='ipaddress',
            name='country',
            field=models.TextField(max_length=32),
        ),
        migrations.AlterField(
            model_name='ipaddress',
            name='isp',
            field=models.TextField(max_length=64),
        ),
        migrations.AlterField(
            model_name='item',
            name='dataset',
            field=models.TextField(db_index=True, max_length=16),
        ),
        migrations.AlterField(
            model_name='item',
            name='dataset_type',
            field=models.TextField(db_index=True, max_length=16),
        ),
        migrations.AlterField(
            model_name='item',
            name='file_format',
            field=models.TextField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='file_type',
            field=models.TextField(max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='name',
            field=models.TextField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='item',
            name='s3_key',
            field=models.TextField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name='lab',
            name='name',
            field=models.TextField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='bucket',
            field=models.TextField(max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='error_code',
            field=models.TextField(db_index=True, max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='key_name',
            field=models.TextField(max_length=32),
        ),
        migrations.AlterField(
            model_name='log',
            name='operation',
            field=models.TextField(max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='request_id',
            field=models.TextField(max_length=16, unique=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='request_uri',
            field=models.TextField(max_length=1024, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='requester',
            field=models.TextField(db_index=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='s3_key',
            field=models.TextField(db_index=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='user_agent',
            field=models.TextField(max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='version_id',
            field=models.TextField(max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='querycountattime',
            name='data_set',
            field=models.TextField(max_length=16),
        ),
    ]