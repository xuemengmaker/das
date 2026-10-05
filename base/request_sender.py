"""统一请求发送入口，避免测试代码散落 requests 调用。"""
import requests


class RequestSender:
    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def send(self, request_spec: dict):
        method = request_spec["method"].upper()
        response = requests.request(
            method=method,
            url=f"{self.base_url}{request_spec['path']}",
            headers=request_spec.get("headers"),
            json=request_spec.get("json"),
            params=request_spec.get("params"),
            timeout=self.timeout,
        )
        return response

