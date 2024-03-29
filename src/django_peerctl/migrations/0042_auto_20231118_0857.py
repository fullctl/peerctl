# Generated by Django 3.2.23 on 2023-11-18 08:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_fullctl", "0032_auto_20230719_1049"),
        ("django_peerctl", "0041_alter_peersession_peer_session_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="peersession",
            name="status",
            field=models.CharField(
                choices=[
                    ("ok", "ok"),
                    ("requested", "requested"),
                    ("configured", "configured"),
                ],
                default="ok",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="OrganizationDefaultNetwork",
            fields=[
                (
                    "org",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="default_network",
                        serialize=False,
                        to="django_fullctl.organization",
                    ),
                ),
                (
                    "network",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="default_for_org",
                        to="django_peerctl.network",
                    ),
                ),
            ],
            options={
                "verbose_name": "Organization Default Network",
                "verbose_name_plural": "Organization Default Network",
                "db_table": "ixctl_default_network",
            },
        ),
    ]
