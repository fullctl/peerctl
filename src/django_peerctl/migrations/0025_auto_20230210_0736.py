# Generated by Django 3.2.17 on 2023-02-10 07:36

import django.db.models.manager
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("django_fullctl", "0026_auto_20230131_1405"),
        ("django_peerctl", "0024_auto_20230209_1327"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncRouteServerMD5",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("django_fullctl.task",),
            managers=[
                ("handleref", django.db.models.manager.Manager()),
            ],
        ),
        migrations.RemoveField(
            model_name="network",
            name="route_server_md5",
        ),
    ]
