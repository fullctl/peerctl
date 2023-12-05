# Generated by Django 3.2.20 on 2023-11-29 09:01

import django.db.models.deletion
import django.db.models.manager
import django_handleref.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0043_alter_organizationdefaultnetwork_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="export_policy_managed",
            field=models.IntegerField(
                blank=True, help_text="FullCtl Managed", null=True
            ),
        ),
        migrations.AddField(
            model_name="policy",
            name="import_policy_managed",
            field=models.IntegerField(
                blank=True, help_text="FullCtl Managed", null=True
            ),
        ),
        migrations.CreateModel(
            name="PolicyPeerGroup",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "Ok"),
                            ("pending", "Pending"),
                            ("deactivated", "Deactivated"),
                            ("failed", "Failed"),
                            ("expired", "Expired"),
                        ],
                        default="ok",
                        max_length=12,
                    ),
                ),
                (
                    "notes_public",
                    models.TextField(blank=True, help_text="public notes", null=True),
                ),
                (
                    "notes_private",
                    models.TextField(blank=True, help_text="private notes", null=True),
                ),
                ("slug", models.SlugField(max_length=255)),
                ("afi", models.SmallIntegerField()),
                ("max_prefixes", models.IntegerField()),
                ("import_policy", models.CharField(max_length=255)),
                ("export_policy", models.CharField(max_length=255)),
                ("enforce_first_asn", models.BooleanField(default=False)),
                ("soft_reconfig", models.BooleanField(default=False)),
                ("allow_asn_in", models.IntegerField()),
                ("multipath", models.BooleanField(default=False)),
                (
                    "net",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="policy_peer_groups",
                        to="django_peerctl.network",
                    ),
                ),
            ],
            options={
                "verbose_name": "Policy Peer Group",
                "verbose_name_plural": "Policy Peer Groups",
                "db_table": "peerctl_policy_peer_group",
                "unique_together": {("slug", "net")},
            },
            managers=[
                ("handleref", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name="policy",
            name="peer_group_managed",
            field=models.ForeignKey(
                blank=True,
                help_text="FullCtl Managed",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="policies",
                to="django_peerctl.policypeergroup",
            ),
        ),
    ]