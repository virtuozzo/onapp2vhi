import click

from inc.vhi_helpers import Vhi
from click_default_group import DefaultGroup


@click.group(cls=DefaultGroup, default='create-service-user', invoke_without_command=True, default_if_no_args=True)
def cli():
    pass


@click.command()
def create_service_user():
    vhi = Vhi()
    vhi.create_service_user()


cli.add_command(create_service_user)
