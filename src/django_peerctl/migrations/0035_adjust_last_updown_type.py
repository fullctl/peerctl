# Generated by Django 3.2.17 on 2023-06-02 11:29

from django.db import migrations


def forwards(apps, schema_editor):
    """
    Function to loop through all PeerSession objects and convert
    meta4 and meta6 last_updown fields to int. Sets it to 0 in case of conversion failure.
    Skips any null or unset last_updown fields.
    """
    PeerSession = apps.get_model("django_peerctl", "PeerSession")

    for peer_session in PeerSession.handleref.all():
        if peer_session.meta4 and "last_updown" in peer_session.meta4:
            try:
                peer_session.meta4["last_updown"] = int(
                    peer_session.meta4["last_updown"]
                )
            except ValueError:
                peer_session.meta4["last_updown"] = 0

        if peer_session.meta6 and "last_updown" in peer_session.meta6:
            try:
                peer_session.meta6["last_updown"] = int(
                    peer_session.meta6["last_updown"]
                )
            except ValueError:
                peer_session.meta6["last_updown"] = 0

        peer_session.save()


class Migration(migrations.Migration):
    dependencies = [
        ("django_peerctl", "0034_auto_20230602_1105"),
    ]

    operations = [
        migrations.RunPython(forwards),  # Add migration function to operations
    ]
