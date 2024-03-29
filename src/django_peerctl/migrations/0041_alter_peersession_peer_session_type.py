# Generated by Django 3.2.14 on 2023-07-05 11:38

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0040_emailtemplate_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="peersession",
            name="peer_session_type",
            field=models.CharField(
                choices=[
                    ("ixp", "IXP"),
                    ("pni", "PNI"),
                    ("transit", "Transit"),
                    ("customer", "Customer"),
                    ("core", "Core"),
                ],
                default="ixp",
                max_length=255,
            ),
        ),
    ]
