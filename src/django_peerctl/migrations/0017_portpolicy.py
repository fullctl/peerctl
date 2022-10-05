# Generated by Django 3.2.15 on 2022-09-20 23:22

import django.db.models.deletion
import django.db.models.manager
import django_handleref.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_peerctl", "0016_auto_20220920_1435"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortPolicy",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(blank=True, max_length=255, verbose_name="Status"),
                ),
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
                (
                    "notes_public",
                    models.TextField(blank=True, help_text="public notes", null=True),
                ),
                (
                    "notes_private",
                    models.TextField(blank=True, help_text="private notes", null=True),
                ),
                ("port", models.PositiveIntegerField(unique=True)),
                (
                    "policy4",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="django_peerctl.policy",
                    ),
                ),
                (
                    "policy6",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="django_peerctl.policy",
                    ),
                ),
            ],
            options={
                "db_table": "peerctl_port_policy",
            },
            managers=[
                ("handleref", django.db.models.manager.Manager()),
            ],
        ),
    ]