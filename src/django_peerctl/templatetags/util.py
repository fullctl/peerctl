from django import template
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django_countries import countries
import datetime

register = template.Library()


@register.filter
def ix_peers(net, ix_id):
    return net.get_peers(ix_id)
