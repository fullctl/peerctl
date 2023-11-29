from django import forms
from django import forms as baseForms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from django_peerctl.models import (
    AuditLog,
    DeviceTemplate,
    EmailLog,
    EmailLogRecipient,
    InternetExchange,
    Network,
    Organization,
    PeerNetwork,
    PeerPort,
    PeerRequest,
    PeerRequestLocation,
    PeerSession,
    Policy,
    PolicyPeerGroup,
    Port,
    PortInfo,
    UserSession,
    Wish,
    ref_fallback,
)


def status_form(choices=None):
    if not choices:
        choices = [
            ("ok", "ok"),
        ]

    class StatusForm(baseForms.ModelForm):
        status = baseForms.ChoiceField(choices=choices)

    return StatusForm


class CachedPortMixin:
    def _cache_ports(self, qs):
        """
        Caches Port instances in _ports
        """

        if hasattr(self, "_ports"):
            return

        self._ports = {
            port.id: port
            for port in Port().objects(
                id__in=[i for i in qs.values_list("port", flat=True)]
            )
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self._cache_ports(qs)
        return qs


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
        "email_override",
    )
    search_fields = ("asn",)
    readonly_fields = ("policy4", "policy6")
    fields = (
        "asn",
        "max_sessions",
        "status",
        "org",
        "as_set_override",
        "prefix4_override",
        "prefix6_override",
        "network_type_override",
    )
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


@admin.register(PeerPort)
class PeerPortAdmin(admin.ModelAdmin):
    list_display = ("id", "peer_net", "port_info", "created", "updated")


@admin.register(PortInfo)
class PortInfoAdmin(CachedPortMixin, admin.ModelAdmin):
    list_display = ("net", "asn", "ref_id", "ip4", "ip6", "port")
    readonly_fields = ("asn", "ix", "ip4", "ip6", "ref_ix_id")
    search_fields = ("net__asn",)
    form = status_form()

    def asn(self, obj):
        return obj.net.asn

    @ref_fallback(None)
    def ip4(self, obj):
        try:
            return self._ports.get(int(obj.port)).ip_address_4
        except (KeyError, AttributeError, TypeError):
            pass

        return obj.ip_address_4 or obj.ref.ipaddr4

    @ref_fallback(None)
    def ip6(self, obj):
        try:
            return self._ports.get(int(obj.port)).ip_address_6
        except (KeyError, AttributeError, TypeError):
            pass

        return obj.ip_address_6 or obj.ref.ipaddr6


@admin.register(DeviceTemplate)
class DeviceTemplateAdmin(admin.ModelAdmin):
    pass


@admin.register(Wish)
class WishAdmin(admin.ModelAdmin):
    list_display = ("user", "path", "text", "ticket", "status", "created")
    form = status_form()


class PeerRequestLocationInline(admin.TabularInline):
    model = PeerRequestLocation
    extra = 0


@admin.register(PeerRequest)
class PeerRequestAdmin(admin.ModelAdmin):
    search_fields = ("net__asn", "peer_asn")
    list_display = ("net", "peer_asn", "type", "status", "created", "updated")

    inlines = (PeerRequestLocationInline,)


@admin.register(PeerSession)
class PeerSessionAdmin(CachedPortMixin, admin.ModelAdmin):
    search_fields = ("peer_port__peer_net__net__asn", "peer_port__peer_net__peer__asn")
    list_display = (
        "id",
        "net",
        "peer",
        "ix_id",
        "ix_name",
        "ip4",
        "ip6",
        "peer_ipaddr4",
        "peer_ipaddr6",
        "policy4",
        "policy6",
        "status",
        "request_status",
        "created",
        "updated",
        "port",
        "device",
    )
    list_filter = ("status",)
    form = status_form(
        choices=[("ok", "ok"), ("requested", "requested"), ("configured", "configured")]
    )

    readonly_fields = ("net", "peer", "policy4", "policy6", "request_status")

    def net(self, obj):
        return obj.peer_port.peer_net.net

    def peer(self, obj):
        return obj.peer_port.peer_net.peer

    @ref_fallback(0)
    def ix_id(self, obj):
        if not obj.port:
            return None

        return self._ports.get(int(obj.port)).port_info_object.ix.id

    @ref_fallback(None)
    def ix_name(self, obj):
        if not obj.port:
            return None

        return self._ports.get(int(obj.port)).port_info_object.ix.name

    @ref_fallback(None)
    def ip4(self, obj):
        if not obj.port:
            return None

        try:
            return self._ports.get(int(obj.port)).ip_address_4
        except (KeyError, AttributeError):
            pass

        return obj.port.object.port_info_object.ipaddr4

    @ref_fallback(None)
    def ip6(self, obj):
        if not obj.port:
            return None

        try:
            return self._ports.get(int(obj.port)).ip_address_6
        except (KeyError, AttributeError):
            pass

        return obj.port.object.port_info_object.ipaddr6

    def peer_ipaddr4(self, obj):
        return obj.peer_port.port_info.ipaddr4

    def peer_ipaddr6(self, obj):
        return obj.peer_port.port_info.ipaddr6

    def request_status(self, obj):
        return obj.status


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


# XXX OLD organization admin - still need?
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "net_count", "created", "updated")
    fields = ("name", "networks")
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
        "import_policy_managed",
        "export_policy",
        "export_policy_managed",
        "peer_group",
        "peer_group_managed",
        "created",
        "updated",
    )
    form = status_form()


@admin.register(PolicyPeerGroup)
class PolicyPeerGroupAdmin(admin.ModelAdmin):
    search_fields = ("slug",)
    list_display = (
        "id",
        "net",
        "slug",
        "created",
        "updated",
    )
    autocomplete_fields = ("net",)

    form = status_form()


@admin.register(InternetExchange)
class IXAdmin(admin.ModelAdmin):
    search_fields = ("name", "name_long", "country")
    list_display = (
        "id",
        "name",
        "name_long",
        "country",
        "ref_id",
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
