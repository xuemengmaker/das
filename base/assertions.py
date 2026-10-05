"""声明式断言执行器，读取 YAML 中的 expected 字段。"""
from base.yaml_parser import json_path_get


def assert_response(response, expected: dict) -> None:
    assert response.status_code == expected["status_code"], response.text
    body = response.json()
    for path, wanted in expected.get("body", {}).items():
        actual = json_path_get(body, path)
        assert actual == wanted, f"{path}: expected={wanted!r}, actual={actual!r}"

