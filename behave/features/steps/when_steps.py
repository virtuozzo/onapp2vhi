from fixtures.helper import cp_helper
import os
import yaml

CHECK_FAILED = False

def get_yaml(entity):

    path = os.path.dirname(os.path.abspath("fixtures/{entity}.yaml".format(entity=entity))) + "/" + entity + ".yaml"
    return yaml.load(open(path).read(), Loader=yaml.FullLoader)

use_step_matcher('parse')
@when('I delete the {entity} ({name})')
def step_impl(context, entity, name):

    entity_plural = cp_helper.convert_to_plural(cp_helper.rephrase_key(entity))
    response = {}

    data = context.cp.search(entity_plural, args=name)
    if not data:
        assert CHECK_FAILED, "error: {name} is not found".format(name=name)

    id = data[0][cp_helper.convert_to_singular(entity_plural)]["id"]
    response[entity_plural] = context.cp.delete(entity_plural, id)

    context.response = response[entity_plural]

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\w\W\s]+)\) with following details')
def step_impl(context, entity, name):

    entity = cp_helper.rephrase_key(entity)
    entity_plural = cp_helper.convert_to_plural(entity)
    data = get_yaml(entity)[name]

    headings = cp_helper.rephrase_key(context.table.headings)
    for heading in headings:
        for row in context.table.rows:
            row.headings = headings
            data[entity][heading] = row[heading]

    print(data)

    context.response = context.cp.create(entity=entity_plural, data=data)

use_step_matcher('re')
@when('I create a? (?P<entity>[\w\s]+) \((?P<name>[\W\w\s]+)\)')
def step_impl(context, entity, name):
    
    entity = cp_helper.rephrase_key(entity)
    config = get_yaml(entity)
    data = config[name]

    if entity == "virtual_machine":
        if data["virtual_machine"].get("template_id"):
            data["virtual_machine"]["template_id"] = context.cp.search("templates", args=data["virtual_machine"]["template_id"], filter=True)[0]["image_template"]["id"]
            
    print(data)

    context.response = context.cp.create(entity=cp_helper.convert_to_plural(entity), data=data)