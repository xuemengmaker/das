import json

import allure
import pytest

from base.assertions import assert_response
from base.request_sender import RequestSender
from base.yaml_parser import extract_variables, load_case, prepare_case
from common.config import load_config
from common.paths import CASE_DIR


@pytest.mark.api
@allure.feature("TDMS 数据平台接口自动化")
def test_tdms_sample_lifecycle(api_base_url):
    """按文件名顺序执行采集、信号输出和预警初筛的接口关联。"""
    sender = RequestSender(api_base_url, timeout=load_config()["api"]["timeout"])
    for case_file in sorted(CASE_DIR.glob("*.yaml")):
        raw_case = load_case(case_file)
        case = prepare_case(raw_case)
        with allure.step(case["name"]):
            allure.attach(json.dumps(case["request"], ensure_ascii=False, indent=2), "请求数据", allure.attachment_type.JSON)
            response = sender.send(case["request"])
            allure.attach(response.text, "响应数据", allure.attachment_type.JSON)
            assert_response(response, case["expected"])
            extract_variables(response.json(), case.get("extract"))
