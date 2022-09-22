# Generated by Django 3.2.15 on 2022-09-17 22:11

import fullctl.django.fields.service_bridge
import fullctl.service_bridge.devicectl
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("django_peerctl", "0014_fix_orgs"),
    ]

    operations = [
        migrations.AddField(
            model_name="portinfo",
            name="port",
            field=fullctl.django.fields.service_bridge.ReferencedObjectField(
                bridge=fullctl.service_bridge.devicectl.Port, default=0
            ),
            preserve_default=False,
        ),
    ]
