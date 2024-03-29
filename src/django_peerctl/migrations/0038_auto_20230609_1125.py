# Generated by Django 3.2.17 on 2023-06-09 11:25

import fullctl.django.fields.service_bridge
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0037_auto_20230605_0835"),
    ]

    operations = [
        migrations.AddField(
            model_name="peerrequestlocation",
            name="peer_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="peerrequestlocation",
            name="port",
            field=fullctl.django.fields.service_bridge.ReferencedObjectField(
                blank=True, bridge=None, null=True
            ),
        ),
    ]
