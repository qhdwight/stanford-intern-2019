# Generated by Django 2.2.3 on 2019-08-02 02:55

import django.contrib.postgres.indexes
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0008_auto_20190801_1927'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='log',
            name='dashboard_l_item_id_7fbb2c_brin',
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['item'], name='dashboard_l_item_id_23d68f_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['time'], name='dashboard_l_time_afed37_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['ip_address'], name='dashboard_l_ip_addr_7a3dc4_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['requester'], name='dashboard_l_request_93aa15_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['requester_type'], name='dashboard_l_request_c5a51a_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['request_id'], name='dashboard_l_request_2116aa_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['s3_key'], name='dashboard_l_s3_key_96bebd_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['http_status'], name='dashboard_l_http_st_20e693_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['error_code'], name='dashboard_l_error_c_5f5a52_brin'),
        ),
        migrations.AddIndex(
            model_name='log',
            index=django.contrib.postgres.indexes.BrinIndex(fields=['object_size'], name='dashboard_l_object__bb7e51_brin'),
        ),
    ]
