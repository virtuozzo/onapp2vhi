from pathlib import Path

import click

from onapp2vhi.utility.config import OnApp2VHIConfig
from onapp2vhi.utility.template import CONFIG_TEMPLATE


def search_config():
    if Path("config.ini").is_file():
        return "config.ini"

    user_config = Path("~/.config/onapp2vhi/config.ini").expanduser()

    if Path(user_config).is_file():
        return user_config
    return None


def generate_example_config(ctx, param, value):
    """
    Generate example config file
    """
    if not value or ctx.resilient_parsing:
        return

    current_path = Path().absolute()
    config_path = current_path.joinpath("config.ini")

    if config_path.exists():
        print("Config file already exists")
        ctx.exit()
        return

    with open(config_path, "w+", encoding="utf8") as conf:
        conf.write(CONFIG_TEMPLATE)
        print("Config file generated")
        ctx.exit()


@click.group()
@click.option(
    "--config",
    default=search_config,
    type=click.Path(exists=True),
    required=True,
    show_default="config.ini or ~/.config/onapp2vhi/config.ini",
)
@click.option(
    "--generate-config",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=generate_example_config,
    help="Generate example config.ini file.",
)
def run(config):
    OnApp2VHIConfig.load_config(config)


@run.command()
@click.option(
    "--props",
    "--properties",
    "--select",
    "--vm-identifier",
    default="",
    help="Select specific params with --select=a,b,c option.",
)
@click.option(
    "--find",
    "--where",
    "--where-arg",
    default="",
    help="Select by specific params with --where='id=13' option.",
)
def list_onapp_users(props="", find=""):
    from inc.onapp_helpers import list_onapp_users as list_onapp_users_impl

    list_onapp_users_impl(props=props, find=find)


@run.command()
@click.option(
    "--props",
    "--properties",
    "--select",
    default="",
    help="Select specific params with --props=a,b,c option.",
)
@click.option(
    "--find",
    "--where",
    "--where-arg",
    default="",
    help="Select by specific params with --where='id=13' option.",
)
def list_onapp_vms(props="", find=""):
    from inc.onapp_helpers import list_onapp_vms as list_onapp_vms_impl

    list_onapp_vms_impl(props=props, find=find)


@run.command()
def create_service_user():
    from inc.vhi_helpers import Vhi

    vhi = Vhi()
    vhi.create_service_user()


@run.command()
@click.option("--user", default="", help="OnApp User, VM identifier.")
@click.option("--network", default="", help="Network to be used")
@click.option("--vm", default="", help="VM to be migrated")
@click.option(
    "--project", default="", help="Project where all objects will be migrated"
)
def migrate_all(user="", network="", vm="", project=""):
    from onapp2vhi.ops.migrate_all import migrate_all_impl

    migrate_all_impl(user=user, network=network, vm=vm, project=project)
