# Generated by Django 3.2.17 on 2023-02-10 09:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0025_auto_20230210_0736"),
    ]

    operations = [
        migrations.AddField(
            model_name="portinfo",
            name="is_route_server_peer",
            field=models.BooleanField(null=True),
        ),
    ]
