# Generated by Django 3.2.17 on 2023-02-10 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_peerctl', '0027_portinfo_mac_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='network',
            name='multicast_override',
            field=models.BooleanField(null=True),
        ),
        migrations.AddField(
            model_name='network',
            name='ratio_override',
            field=models.CharField(blank=True, choices=[('', 'Not Disclosed'), ('Not Disclosed', 'Not Disclosed'), ('Heavy Outbound', 'Heavy Outbound'), ('Mostly Outbound', 'Mostly Outbound'), ('Balanced', 'Balanced'), ('Mostly Inbound', 'Mostly Inbound'), ('Heavy Inbound', 'Heavy Inbound')], max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='network',
            name='scope_override',
            field=models.CharField(blank=True, choices=[('', 'Not Disclosed'), ('Not Disclosed', 'Not Disclosed'), ('Regional', 'Regional'), ('North America', 'North America'), ('Asia Pacific', 'Asia Pacific'), ('Europe', 'Europe'), ('South America', 'South America'), ('Africa', 'Africa'), ('Australia', 'Australia'), ('Middle East', 'Middle East'), ('Global', 'Global')], max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='network',
            name='traffic_override',
            field=models.CharField(blank=True, choices=[('', 'Not Disclosed'), ('0-20Mbps', '0-20Mbps'), ('20-100Mbps', '20-100Mbps'), ('100-1000Mbps', '100-1000Mbps'), ('1-5Gbps', '1-5Gbps'), ('5-10Gbps', '5-10Gbps'), ('10-20Gbps', '10-20Gbps'), ('20-50Gbps', '20-50Gbps'), ('50-100Gbps', '50-100Gbps'), ('100-200Gbps', '100-200Gbps'), ('200-300Gbps', '200-300Gbps'), ('300-500Gbps', '300-500Gbps'), ('500-1000Gbps', '500-1000Gbps'), ('1-5Tbps', '1-5Tbps'), ('5-10Tbps', '5-10Tbps'), ('10-20Tbps', '10-20Tbps'), ('20-50Tbps', '20-50Tbps'), ('50-100Tbps', '50-100Tbps'), ('100+Tbps', '100+Tbps')], max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='network',
            name='unicast_override',
            field=models.BooleanField(null=True),
        ),
    ]
