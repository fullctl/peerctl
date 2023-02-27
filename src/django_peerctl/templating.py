def make_variable_name(value):
    return f"{value}".replace(" ", "_").replace(".", "_")
    # FIXME: make this work magically, or wait until we are on py3
    # trans = string.maketrans(u" .", u"__")
    # return string.translate(u"{}".format(value), trans)
