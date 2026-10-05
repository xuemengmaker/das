import threading

import pytest
from werkzeug.serving import make_server

from base.variable_store import clear_variables
from common.config import load_config
from mock_server.app import create_app


@pytest.fixture(scope="session", autouse=True)
def reset_extract_file():
    """每次测试前清空 extract.yaml，避免上次执行污染接口关联。"""
    clear_variables()


@pytest.fixture(scope="session")
def api_base_url():
    """在空闲端口启动本地 TDMS 服务，测试结束后自动关闭。"""
    # 测试数据根目录由 conf/config.yaml 管理，服务仅做只读元数据访问。
    data_root = load_config()["tdms"]["data_root"]
    server = make_server("127.0.0.1", 0, create_app(data_root=data_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)
