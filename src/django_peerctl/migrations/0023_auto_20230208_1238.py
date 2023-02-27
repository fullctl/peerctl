# Generated by Django 3.2.16 on 2023-02-08 12:38

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0022_auto_20230124_1528"),
    ]

    operations = [
        migrations.AddField(
            model_name="network",
            name="prefix4_override",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="network",
            name="prefix6_override",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
