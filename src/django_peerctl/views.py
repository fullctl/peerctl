from django.conf import settings
from django.shortcuts import redirect, render
from fullctl.django.decorators import load_instance, require_auth

from django_peerctl.models import Network
from django_peerctl.utils import verified_asns

# Create your views here.


def make_env(request, **kwargs):
    r = {"env": settings.RELEASE_ENV, "version": settings.PACKAGE_VERSION}
    r.update(**kwargs)
    return r


@require_auth()
@load_instance()
def view_instance(request, instance, **kwargs):
    env = make_env(request, instance=instance, org=instance.org)

    selected_asn = 0
    # check if asn specified in request
    asn = request.GET.get("asn")

    default_asn = None
    default_net = Network.get_default_network_for_org(instance.org)
    if default_net is not None:
        default_asn = default_net.asn

    if asn is None:
        asn = default_asn

    if asn is not None:
        request.session["asn"] = asn
        selected_asn = int(asn)

    asns = {net.asn: net for net in verified_asns(request.perms, org=instance.org)}

    net = asns.get(selected_asn)

    if not net:
        for net in asns.values():
            break

    if not net:
        env["selected_asn"] = None
    else:
        env["selected_asn"] = net.asn

    env["forms"] = {}
    env["net"] = net
    env["asns"] = asns
    env["asns_count"] = len(asns)
    env["default_asn"] = default_asn

    return render(request, "theme-select.html", env)


@require_auth()
def org_redirect(request):
    return redirect(f"/{request.org.slug}/")
