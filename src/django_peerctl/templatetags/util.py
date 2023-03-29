from django import template

# from django.utils.translation import ugettext_lazy as _

register = template.Library()


@register.filter
def ix_peers(net, ix_id):
    return net.get_peers(ix_id)