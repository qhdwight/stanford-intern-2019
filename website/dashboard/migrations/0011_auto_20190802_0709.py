# Generated by Django 2.2.3 on 2019-08-02 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0010_auto_20190802_0634'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_item_id_23d68f_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_ip_addr_7a3dc4_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_request_93aa15_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_request_c5a51a_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_request_2116aa_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_s3_key_96bebd_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_http_st_20e693_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_error_c_5f5a52_brin',
        ),
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_object__bb7e51_brin',
        ),
        migrations.AlterField(
            model_name='log',
            name='error_code',
            field=models.TextField(db_index=True, max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='http_status',
            field=models.PositiveSmallIntegerField(db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='ip_address',
            field=models.GenericIPAddressField(db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='object_size',
            field=models.BigIntegerField(db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='request_id',
            field=models.TextField(db_index=True, max_length=16),
        ),
        migrations.AlterField(
            model_name='log',
            name='requester',
            field=models.TextField(db_index=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='requester_type',
            field=models.PositiveSmallIntegerField(db_index=True),
        ),
        migrations.AlterField(
            model_name='log',
            name='s3_key',
            field=models.TextField(db_index=True, max_length=64, null=True),
        ),
    ]