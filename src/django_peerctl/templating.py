import ipaddress
from typing import Union

__all__ =[
    "make_variable_name",
    "ip_version",
]

def make_variable_name(value):
    return f"{value}".replace(" ", "_").replace(".", "_")
    # FIXME: make this work magically, or wait until we are on py3
    # trans = string.maketrans(u" .", u"__")
    # return string.translate(u"{}".format(value), trans)


def ip_version(ip:str) -> Union[int, None]:
    try:
        ip_interface = ipaddress.ip_interface(str(ip))
        return ip_interface.version
    except ValueError:
        return None