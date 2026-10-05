"""跨接口变量存储：所有提取值都落盘到 extract.yaml，便于观察接口关联。"""
from pathlib import Path

import yaml

EXTRACT_FILE = Path(__file__).with_name("extract.yaml")


def load_variables() -> dict:
    with EXTRACT_FILE.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def save_variables(values: dict) -> None:
    data = load_variables()
    data.update(values)
    with EXTRACT_FILE.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)


def clear_variables() -> None:
    with EXTRACT_FILE.open("w", encoding="utf-8") as file:
        yaml.safe_dump({}, file)

