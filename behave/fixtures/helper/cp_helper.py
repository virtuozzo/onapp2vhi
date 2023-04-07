to_singular = {"virtual_machines": "virtual_machine"}
to_plural = {"virtual_machine": "virtual_machines"}

def rephrase_key(data):
    """
    Rephrase word from white space " " to underscore "_", eg. virtual machine > virtual_machine
    :param data: String
    :return: New converted String
    """
    data_list = []

    if isinstance(data, list):

        for key in data:
            key = key.replace(" ", "_")

            data_list.append(key)

        return data_list

    elif isinstance(data, str):
        if " " in data:
            return data.replace(" ", "_")
        else:
            return data

def convert_to_plural(entity):
    """
    To convert singular to plural phrase
    :param entity: edge_group
    :return: edge_groups
    """
    return to_plural.get(entity, entity)

def convert_to_singular(entity):
    """
    To convert plural to singular phrase
    :param entity: edge_groups
    :return: edge_group
    """
    return to_singular.get(entity, entity)