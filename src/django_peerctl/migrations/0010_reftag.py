# Generated by Django 3.2.12 on 2022-07-12 13:20

import django.core.validators
import django.db.models.deletion
import django.db.models.manager
import django_inet.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_fullctl", "0019_default_org"),
        ("django_peerctl", "0009_auto_20211019_1133"),
    ]

    operations = [
        migrations.CreateModel(
            name="SyncASSet",
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
        migrations.RenameField(
            model_name="emaillogrecipient",
            old_name="emaillog",
            new_name="email_log",
        ),
        migrations.RenameField(
            model_name="peerport",
            old_name="peernet",
            new_name="peer_net",
        ),
        migrations.RenameField(
            model_name="peerport",
            old_name="portinfo",
            new_name="port_info",
        ),
        migrations.RenameField(
            model_name="peersession",
            old_name="peerport",
            new_name="peer_port",
        ),
        migrations.RenameField(
            model_name="port",
            old_name="portinfo",
            new_name="port_info",
        ),
        migrations.RenameField(
            model_name="port",
            old_name="virtport",
            new_name="virtual_port",
        ),
        migrations.RenameField(
            model_name="physicalport",
            old_name="logport",
            new_name="logical_port",
        ),
        migrations.RenameField(
            model_name="virtualport",
            old_name="logport",
            new_name="logical_port",
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="event",
            field=models.CharField(
                choices=[
                    ("peer_session-request", "Peering Request"),
                    ("peer_session-add", "Session Add"),
                    ("peer_session-del", "Session Delete"),
                    ("peer_session-mod", "Session Modify"),
                    ("policy-mod", "Policy Modify"),
                    ("email", "Email"),
                ],
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="emaillog",
            name="net",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="qset_email_log",
                to="django_peerctl.network",
            ),
        ),
        migrations.AlterField(
            model_name="emaillog",
            name="origin",
            field=models.CharField(
                choices=[
                    ("peer_session-workflow", "Peering Session Workflow"),
                    ("bulk-email", "Notification Email"),
                ],
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="network",
            name="asn",
            field=django_inet.models.ASNField(
                db_index=True,
                unique=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MinValueValidator(0),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="peersession",
            name="port",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="peer_session_qs",
                to="django_peerctl.port",
            ),
        ),
        migrations.AlterField(
            model_name="physicalport",
            name="device",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="physical_port_qs",
                to="django_peerctl.device",
            ),
        ),
        migrations.AlterField(
            model_name="portinfo",
            name="net",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="port_info_qs",
                to="django_peerctl.network",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="peersession",
            unique_together={("port", "peer_port")},
        ),
        migrations.AlterModelTable(
            name="devicetemplate",
            table="peerctl_device_template",
        ),
        migrations.AlterModelTable(
            name="emaillog",
            table="peerctl_email_log",
        ),
        migrations.AlterModelTable(
            name="emaillogrecipient",
            table="peerctl_email_log_recipient",
        ),
        migrations.AlterModelTable(
            name="emailtemplate",
            table="peerctl_email_template",
        ),
        migrations.AlterModelTable(
            name="logicalport",
            table="peerctl_logical_port",
        ),
        migrations.AlterModelTable(
            name="peernetwork",
            table="peerctl_peer_net",
        ),
        migrations.AlterModelTable(
            name="peerport",
            table="peerctl_peer_port",
        ),
        migrations.AlterModelTable(
            name="peersession",
            table="peerctl_peer_session",
        ),
        migrations.AlterModelTable(
            name="physicalport",
            table="peerctl_physical_port",
        ),
        migrations.AlterModelTable(
            name="portinfo",
            table="peerctl_port_info",
        ),
        migrations.AlterModelTable(
            name="userpreferences",
            table="peerctl_user",
        ),
        migrations.AlterModelTable(
            name="virtualport",
            table="peerctl_virtual_port",
        ),
    ]
