import os


from django.conf import settings as dj_settings
from django.contrib.auth import authenticate, logout, login
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseNotFound,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import redirect, render
from django.template import RequestContext, loader
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

from django_grainy.util import Permissions

# from django_peerctl import settings

base_env = {}

# -- util ----


from django_peerctl.stats import site_stats
from django_peerctl import models, const


def emltmpl_base(request, template_id):
    try:
        emltmpl = models.EmailTemplate(type=template_id)
        path = os.path.join(emltmpl.template_loader_paths[0], emltmpl.template_path)
        with open(path) as fh:
            template_text = fh.read()
    except KeyError:
        return HttpResponse(status=404)
    return HttpResponse(template_text)


def devicetmpl_base(request, template_id):
    try:
        path = os.path.join(
            dj_settings.NETOM_TEMPLATE_DIR, const.DEVICE_TEMPLATES[template_id]
        )
        with open(path) as fh:
            template_text = fh.read()
    except KeyError:
        return HttpResponse(status=404)
    return HttpResponse(template_text)
