# Generated by Django 3.2.7 on 2021-10-15 08:56

import django.core.validators
from django.db import migrations, models
import django_inet.models


def reset(apps, schema_editor):

    Network = apps.get_model("django_peerctl", "Network")
    InternetExchange = apps.get_model("django_peerctl", "InternetExchange")
    Network.handleref.all().delete()
    InternetExchange.handleref.all.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('django_peerctl', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='internetexchange',
            name='ixlan_id',
        ),
        migrations.RemoveField(
            model_name='portinfo',
            name='netixlan_id',
        ),
        migrations.AddField(
            model_name='internetexchange',
            name='ref_id',
            field=models.CharField(blank=True, null=True, default=None, max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='portinfo',
            name='ref_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='network',
            name='asn',
            field=django_inet.models.ASNField(db_index=True, unique=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MinValueValidator(0), django.core.validators.MinValueValidator(0)]),
        ),
        migrations.RunPython(reset),
    ]
