# Generated by Django 3.2.14 on 2023-06-08 14:16

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0039_devicetemplate_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailtemplate",
            name="default",
            field=models.BooleanField(default=False),
        ),
    ]
