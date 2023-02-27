import os

from django.conf import settings as dj_settings
from django.http import HttpResponse

from django_peerctl import const, models

base_env = {}


def email_template_base(request, template_id):
    try:
        email_template = models.EmailTemplate(type=template_id)
        path = os.path.join(
            email_template.template_loader_paths[0], email_template.template_path
        )
        with open(path) as fh:
            template_text = fh.read()
    except KeyError:
        return HttpResponse(status=404)
    return HttpResponse(template_text)


def device_template_base(request, template_id):
    try:
        path = os.path.join(
            dj_settings.NETOM_TEMPLATE_DIR, const.DEVICE_TEMPLATES[template_id]
        )
        with open(path) as fh:
            template_text = fh.read()
    except KeyError:
        return HttpResponse(status=404)
    return HttpResponse(template_text)
