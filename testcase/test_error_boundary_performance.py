"""补充简历中“异常、边界、性能”测试点的可执行证据。"""
from time import perf_counter

import allure
import pytest

from base.request_sender import RequestSender


def first_tdms_file(sender: RequestSender) -> str:
    response = sender.send({"method": "GET", "path": "/api/v1/tdms/files", "params": {"hour": "00", "limit": 1}})
    assert response.status_code == 200
    return response.json()["data"]["files"][0]["relative_path"]


@pytest.mark.api
@allure.feature("DAS 仪器接口异常与边界测试")
def test_acquisition_rejects_unsupported_sample_rate(api_base_url):
    sender = RequestSender(api_base_url)
    source_file = first_tdms_file(sender)
    response = sender.send({
        "method": "POST",
        "path": "/api/v1/acquisition/tasks",
        "json": {
            "device_id": "DAS-001", "source_file": source_file, "sampling_rate_hz": 500,
            "channel_start": 1, "channel_end": 16, "duration_seconds": 10,
        },
    })
    assert response.status_code == 422
    assert response.json()["code"] == 4223


@pytest.mark.api
@allure.feature("DAS 仪器接口异常与边界测试")
def test_quality_check_rejects_out_of_range_channel(api_base_url):
    sender = RequestSender(api_base_url)
    source_file = first_tdms_file(sender)
    response = sender.send({
        "method": "POST",
        "path": "/api/v1/tdms/quality-check",
        "json": {"relative_path": source_file, "channels_one_based": [4001], "start_sample": 0, "n_samples": 1000},
    })
    assert response.status_code == 422
    assert response.json()["code"] == 4222


@pytest.mark.api
@allure.feature("DAS 信号质量性能冒烟")
def test_quality_check_finishes_within_two_seconds(api_base_url):
    sender = RequestSender(api_base_url)
    source_file = first_tdms_file(sender)
    started_at = perf_counter()
    response = sender.send({
        "method": "POST",
        "path": "/api/v1/tdms/quality-check",
        "json": {"relative_path": source_file, "channels_one_based": [1, 2], "start_sample": 0, "n_samples": 1000},
    })
    elapsed = perf_counter() - started_at
    assert response.status_code == 200
    assert elapsed < 2.0, f"质量检查耗时 {elapsed:.3f}s，超过 2.0s 冒烟阈值"
