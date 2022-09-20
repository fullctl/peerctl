from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from fullctl.django.decorators import load_instance, require_auth

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

    selected_asn = int(request.GET.get("asn", 0))
    asns = {net.asn: net for net in verified_asns(request.perms, org=instance.org)}

    net = asns.get(selected_asn)

    if not net:
        for net in asns.values():
            break

    if not net:
        return HttpResponse(status=401)

    env["forms"] = {}
    env["net"] = net
    env["selected_asn"] = net.asn
    env["asns"] = asns

    return render(request, "peerctl/index.html", env)


@require_auth()
def org_redirect(request):
    return redirect(f"/{request.org.slug}/")
