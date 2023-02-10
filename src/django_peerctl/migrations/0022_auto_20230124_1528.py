# Generated by Django 3.2.16 on 2023-01-24 15:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0021_session_meta"),
    ]

    operations = [
        migrations.AddField(
            model_name="network",
            name="from_email_override",
            field=models.EmailField(
                blank=True,
                help_text="Will override the from: address for email communications from this network",
                max_length=254,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="network",
            name="email_override",
            field=models.EmailField(
                blank=True,
                help_text="Will override the reply-to: address for email communications from this network",
                max_length=254,
                null=True,
            ),
        ),
    ]
