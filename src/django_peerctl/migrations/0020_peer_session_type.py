# Generated by Django 3.2.16 on 2022-12-08 07:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_peerctl", "0019_network_email_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="peersession",
            name="peer_session_type",
            field=models.CharField(
                choices=[
                    ("peer", "Peer"),
                    ("transit", "Transit"),
                    ("customer", "Customer"),
                    ("core", "Core"),
                ],
                default="peer",
                max_length=255,
            ),
        ),
    ]
