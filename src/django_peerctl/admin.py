from django import forms
from django.contrib import admin
from django import forms as baseForms

from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from django_peerctl.models import (
    Organization,
    Network,
    InternetExchange,
    PeerNetwork,
    Device,
    LogicalPort,
    PhysicalPort,
    VirtualPort,
    Port,
    PortInfo,
    PeerSession,
    Wish,
    AuditLog,
    EmailLog,
    EmailLogRecipient,
    Policy,
    UserSession,
)


def status_form(choices=None):
    if not choices:
        choices = [
            ("ok", "ok"),
        ]

    class StatusForm(baseForms.ModelForm):
        status = baseForms.ChoiceField(choices=choices)

    return StatusForm


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asn",
        "name",
        "org",
        "policy4",
        "policy6",
        "created",
        "updated",
    )
    search_fields = ("asn", "name")
    readonly_fields = ("policy4", "policy6")
    fields = ("asn", "max_sessions", "status")
    form = status_form()


@admin.register(PeerNetwork)
class PeerNetworkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "net",
        "peer",
        "md5_set",
        "info_prefixes4",
        "info_prefixes6",
        "created",
        "updated",
    )
    search_fields = ("net__asn", "peer__asn")

    def md5_set(self, obj):
        if obj.md5:
            return "yes"
        return "no"


class PhysicalPortInlineAdmin(admin.TabularInline):
    model = PhysicalPort
    readonly_fields = ("created", "updated")
    fields = ("name", "description", "device", "created", "updated", "status")
    form = status_form()


class VirtualPortInlineAdmin(admin.TabularInline):
    model = VirtualPort
    readonly_fields = ("created", "updated")
    fields = ("vlan_id", "created", "updated", "status")
    form = status_form()


@admin.register(LogicalPort)
class LogicalPortAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "channel", "trunk")
    readonly_fields = ("created", "updated")
    inlines = (PhysicalPortInlineAdmin, VirtualPortInlineAdmin)
    form = status_form()


@admin.register(PortInfo)
class PortInfoAdmin(admin.ModelAdmin):
    list_display = ("asn", "pdb", "ix", "ipaddr4", "ipaddr6")
    readonly_fields = ("asn", "ix", "ipaddr4", "ipaddr6")
    search_fields = ("net__asn",)
    form = status_form()

    def asn(self, obj):
        return obj.net.asn

    def ix(self, obj):
        return obj.ix_name

    def pdb(self, obj):
        try:
            return obj.pdb.id
        except:
            return f"PDB Missing (id={obj.netixlan_id})"


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "portinfo",
        "asn",
        "virtport_id",
        "policy4",
        "policy6",
        "created",
        "updated",
    )
    readonly_fields = ("asn", "policy4", "policy6")
    form = status_form()

    def asn(self, obj):
        return obj.portinfo.net.asn


@admin.register(Wish)
class WishAdmin(admin.ModelAdmin):
    list_display = ("user", "path", "text", "ticket", "status", "created")
    form = status_form()


@admin.register(PeerSession)
class PeerSessionAdmin(admin.ModelAdmin):
    search_fields = ("peerport__peernet__net__asn", "peerport__peernet__peer__asn")
    list_display = (
        "id",
        "net",
        "peer",
        "ix_id",
        "ix_name",
        "ipaddr4",
        "ipaddr6",
        "peer_ipaddr4",
        "peer_ipaddr6",
        "port_id",
        "policy4",
        "policy6",
        "status",
        "created",
        "updated",
    )
    list_filter = ("status",)
    form = status_form(
        choices=[("ok", "ok"), ("requested", "requested"), ("configured", "configured")]
    )

    readonly_fields = ("net", "peer", "policy4", "policy6")

    def net(self, obj):
        return obj.peerport.peernet.net

    def peer(self, obj):
        return obj.peerport.peernet.peer

    def ix_id(self, obj):
        return obj.port.portinfo.ix.id

    def ix_name(self, obj):
        return obj.port.portinfo.ix.name

    def ipaddr4(self, obj):
        return obj.port.portinfo.ipaddr4

    def ipaddr6(self, obj):
        return obj.port.portinfo.ipaddr6

    def peer_ipaddr4(self, obj):
        return obj.peerport.portinfo.ipaddr4

    def peer_ipaddr6(self, obj):
        return obj.peerport.portinfo.ipaddr6


class OrganizationForm(forms.ModelForm):
    """
    Django doesn't come with a premade way to add existing
    objects as relationships, so we make a form that provides
    a field to add and remove networks for an organization
    """

    class Meta:
        model = Organization
        fields = ("name", "networks")

    # add / remove networks through filtered select widget
    networks = forms.ModelMultipleChoiceField(
        queryset=Network.objects.filter(status="ok"),
        widget=admin.widgets.FilteredSelectMultiple("Networks", is_stacked=False),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["networks"].initial = self.instance.net_set.all()

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self.fields["networks"].initial.update(org=None)
        instance.save()
        self.cleaned_data["networks"].update(org=instance)
        return instance


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "net_count", "created", "updated")
    fields = ("name", "networks", "max_sessions")
    readonly_fields = ("net_count",)
    search_fields = ("name", "net_set__asn")
    form = OrganizationForm

    def net_count(self, obj):
        return obj.net_set.all().count()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("net", "event", "user", "data", "created")
    readonly_fields = ("created", "updated", "version")
    form = status_form()


class EmailLogRecipientInline(admin.TabularInline):
    model = EmailLogRecipient
    fields = ("email", "asn")
    form = status_form()


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    search_fields = ("net__asn", "sender_address", "qset_recipient__email")
    list_display = (
        "net",
        "origin",
        "user",
        "sender_address",
        "subject",
        "recipients",
        "recipient",
        "created",
    )
    inlines = (EmailLogRecipientInline,)
    readonly_fields = ("recipients", "created", "updated", "version")
    form = status_form()


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    search_fields = ("net__asn", "name")
    list_display = (
        "id",
        "net",
        "name",
        "import_policy",
        "export_policy",
        "peer_group",
        "created",
        "updated",
    )
    form = status_form()


@admin.register(InternetExchange)
class IXAdmin(admin.ModelAdmin):
    search_fields = ("name", "name_long", "country")
    list_display = (
        "id",
        "name",
        "name_long",
        "country",
        "ixlan_id",
        "created",
        "updated",
    )
    form = status_form()


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class ExtendedUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ("is_active", "last_login", "sessions")
    readonly_fields = ("sessions",)

    def sessions(self, obj):
        return UserSession.objects.filter(user=obj).count()
