import yaml

from common.paths import CONFIG_FILE


def load_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)

