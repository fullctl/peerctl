import os


def discover_netom_templates(device_types, netom_template_dir):
    templates = {}
    template_choices = []

    print("Discovering netom device templates ...")

    if not os.path.isdir(netom_template_dir):
        raise OSError(f"netom0 template directory missing: {netom_template_dir}")

    for devtyp, devlabel in device_types:
        if devtyp == "bird":
            netomtyp = "bird1"
        else:
            netomtyp = devtyp

        tmpl_path = os.path.join(netom_template_dir, f"{netomtyp}-0", "bgp")

        if not os.path.isdir(tmpl_path):
            continue

        for file_name in os.listdir(tmpl_path):
            file_label, ext = os.path.splitext(file_name)
            template_id = f"{devtyp}-bgp-{file_label}"
            template_label = f"{devlabel} BGP {file_label}"
            file_path = os.path.join(tmpl_path, file_name)
            templates[template_id] = file_path.replace(netom_template_dir + "/", "")
            print(f"{template_id}: {templates[template_id]}")
            template_choices.append((template_id, template_label))

    return templates, template_choices
