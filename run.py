"""Windows 下的统一入口：python run.py。"""

import pytest

from common.paths import REPORT_DIR


if __name__ == "__main__":
    REPORT_DIR.mkdir(exist_ok=True)
    pytest.main([
        "-v",
        "--alluredir=report/allure-results",
        "--clean-alluredir",
        "--junitxml=report/junit.xml",
        "testcase",
    ])
