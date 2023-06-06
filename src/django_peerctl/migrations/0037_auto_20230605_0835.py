# Generated by Django 3.2.17 on 2023-06-05 08:35

import django.db.models.deletion
import django.db.models.manager
import django_handleref.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0036_autopeerrequest_peerrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="peerrequest",
            name="notes",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="peerrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ],
                default="pending",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="PeerRequestLocation",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "created",
                    django_handleref.models.CreatedDateTimeField(
                        auto_now_add=True, verbose_name="Created"
                    ),
                ),
                (
                    "updated",
                    django_handleref.models.UpdatedDateTimeField(
                        auto_now=True, verbose_name="Updated"
                    ),
                ),
                ("version", models.IntegerField(default=0)),
                ("pdb_ix_id", models.PositiveIntegerField(blank=True, null=True)),
                ("ixctl_ix_id", models.PositiveIntegerField(blank=True, null=True)),
                ("notes", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=32,
                    ),
                ),
                (
                    "peer_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locations",
                        to="django_peerctl.peerrequest",
                    ),
                ),
            ],
            options={
                "verbose_name": "Peer Request Location",
                "verbose_name_plural": "Peer Request Locations",
                "db_table": "peerctl_peerrequest_location",
            },
            managers=[
                ("handleref", django.db.models.manager.Manager()),
            ],
        ),
    ]
