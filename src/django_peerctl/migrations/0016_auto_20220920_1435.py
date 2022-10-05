# Generated by Django 3.2.15 on 2022-09-20 14:35

import fullctl.django.fields.service_bridge
import netfields.fields
from django.db import migrations

import django_peerctl.models.peerctl


class Migration(migrations.Migration):

    dependencies = [
        ("django_peerctl", "0015_portinfo_port"),
    ]

    operations = [
        migrations.AddField(
            model_name="portinfo",
            name="ip_address_4",
            field=netfields.fields.InetAddressField(
                blank=True,
                help_text="manually set the ip6 address of this port info - used for manual peer session",
                max_length=39,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="portinfo",
            name="ip_address_6",
            field=netfields.fields.InetAddressField(
                blank=True,
                help_text="manually set the ip4 address of this port info - used for manual peer session",
                max_length=39,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="peersession",
            name="port",
            field=fullctl.django.fields.service_bridge.ReferencedObjectField(
                bridge=django_peerctl.models.peerctl.Port
            ),
        ),
        migrations.AlterField(
            model_name="portinfo",
            name="port",
            field=fullctl.django.fields.service_bridge.ReferencedObjectField(
                bridge=django_peerctl.models.peerctl.Port
            ),
        ),
    ]