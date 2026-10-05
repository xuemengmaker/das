"""加载 YAML 用例、替换 ${变量}，并从 JSON 响应提取变量。"""
import re
from copy import deepcopy
from pathlib import Path

import yaml

from base.variable_store import load_variables, save_variables

VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_case(case_file: Path) -> dict:
    with case_file.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def replace_variables(value):
    """递归替换请求中的 ${name}；整段变量保留原始数据类型。"""
    variables = load_variables()
    if isinstance(value, dict):
        return {key: replace_variables(item) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_variables(item) for item in value]
    if not isinstance(value, str):
        return value

    full_match = VARIABLE_PATTERN.fullmatch(value)
    if full_match:
        return variables[full_match.group(1)]

    return VARIABLE_PATTERN.sub(lambda match: str(variables[match.group(1)]), value)


def json_path_get(payload: dict, path: str):
    """支持 demo 所需的 $.data.token 形式路径。"""
    if not path.startswith("$."):
        raise ValueError(f"仅支持以 $. 开头的 JSONPath: {path}")
    current = payload
    for key in path[2:].split("."):
        current = current[int(key)] if isinstance(current, list) else current[key]
    return current


def extract_variables(response_json: dict, extract_rules: dict | None) -> None:
    if not extract_rules:
        return
    values = {name: json_path_get(response_json, path) for name, path in extract_rules.items()}
    save_variables(values)


def prepare_case(case: dict) -> dict:
    return replace_variables(deepcopy(case))
