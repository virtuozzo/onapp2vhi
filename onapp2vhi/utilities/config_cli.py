from paramiko import config
import questionary
from pathlib import Path
from onapp2vhi.utilities.config import OnApp2VHIConfig

def search_config():
    if Path("config.ini").is_file():
        return "config.ini"

    user_config = Path("~/.config/onapp2vhi/config.ini").expanduser()

    if Path(user_config).is_file():
        return user_config
    return None


class ConfigCli:

    def __init__(self, config_path=None):
        self._config = OnApp2VHIConfig.load_config(config_path)
        self._config_sections = ["onapp", "vhi"]

    def run(self):


        while True:
            try:
                section = questionary.select("Which section to edit?", choices=self._config_sections).unsafe_ask()
                self._edit_section(section)
            except KeyboardInterrupt:
                questionary.print("Exit config cli", style="bold fg:red")
                break

    def _edit_section(self, section):

        custom_style = questionary.Style([("highlighted", "bold")])

        while True:
            try:
                section_values = [f"{key}: {value}" for key, value in self._config.get_config(section).items()]

                section_field = questionary.select(f"Which field of {section} to edit", choices=section_values, style=custom_style).unsafe_ask()
                section_field = section_field.split(":")[0]

                update_field = questionary.text(f"Update {section_field} field to ->").ask(kbi_msg="Cancel")
                if update_field:
                    self._config.update(section, section_field, update_field)
                    questionary.print(f"{section} {section_field} field updated", style="fg:blue")
            except KeyboardInterrupt:
                questionary.print("Back to config section", style="bold fg:red")
                break
