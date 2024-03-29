# Generated by Django 3.2.7 on 2021-10-19 10:40

import django.core.validators
import django_inet.models
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0007_mac_address_field"),
    ]

    operations = [
        migrations.RenameField(
            model_name="network",
            old_name="as_set",
            new_name="as_set_override",
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
    ]
