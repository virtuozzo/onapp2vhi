from pathlib import Path

import click
import onapp2vhi
import os

from onapp2vhi.utilities.config import OnApp2VHIConfig
from onapp2vhi.utilities.template import CONFIG_TEMPLATE
from onapp2vhi.utilities.logs.logger import setup_logger


cfg = None


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
    "--log-output-path",
    default=os.getcwd,
    type=click.Path(),
    help="Save migration full log in specified folder",
    show_default="migration_logs/",
)
@click.version_option(onapp2vhi.__version__)
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
@click.version_option(onapp2vhi.__version__)
def run(config, log_output_path):
    global cfg
    setup_logger(log_output_path)
    cfg = OnApp2VHIConfig.load_config(config)


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
    from onapp2vhi.inc.onapp_helpers import (
        list_onapp_users as list_onapp_users_impl,
    )

    list_onapp_users_impl(cfg, props=props, find=find)


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
    from onapp2vhi.inc.onapp_helpers import (
        list_onapp_vms as list_onapp_vms_impl,
    )

    list_onapp_vms_impl(cfg, props=props, find=find)


@run.command()
def create_service_user():
    from onapp2vhi.inc.vhi_helpers import Vhi

    vhi = Vhi(cfg)
    vhi.create_service_user()


@run.command()
@click.option("--user", default="", help="OnApp User, VM identifier.")
@click.option(
    "--vm",
    default="",
    help="Comma separated virtual machines 'oih783gcvy,982h3buisb,893hviun'",
)
@click.option(
    "--project", default="", help="Project where all objects will be migrated"
)
@click.option(
    "--cloud_init_install",
    default="",
    help="Boolean flag, set `false` to NOT install cloud_init_install",
)
@click.option(
    "--placement",
    default="",
    help="Boolean flag, set `false` to NOT install cloud_init_install"
)
@click.option(
    "--vz_guest_tools_install",
    default="",
    help="Boolean flag, set `false` to NOT install vz_guest_tools_install",
)
def migrate(
    user="",
    vm="",
    project="",
    vz_guest_tools_install="true",
    cloud_init_install="true",
    placement=""
):
    from onapp2vhi.ops.migrate import migrate_impl

    migrate_impl(
        cfg,
        user=user,
        vm=vm,
        project=project,
        vz_guest_tools_install=vz_guest_tools_install,
        cloud_init_install=cloud_init_install,
        placement=placement,
    )
