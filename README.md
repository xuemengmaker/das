# DAS 仪器测试接口自动化练习

这是依据“分布式光纤传感监测系统测试开发实习”职责抽象复现的本地练习工程。它用于学习并展示软件测试侧的接口自动化：采集参数校验、信号输出质量检查、告警判断、背景初筛、异常/边界/性能冒烟与回归报告。

服务仅读取 `F:\数据` 下真实 TDMS 文件，绝不写入、移动或删除原始数据。

## 能支撑的实习内容

| 简历职责 | 本工程中的可执行证据 |
| --- | --- |
| 功能测试 | 设备状态、文件查询、采集任务、任务查询、信号质量、告警、背景初筛共 7 个业务步骤 |
| 边界与异常测试 | 不支持采样率、超范围通道号返回明确的 422 错误 |
| 性能测试 | 1,000 样点、2 通道质量检查的 2 秒性能冒烟阈值 |
| Python + pytest 自动化/回归 | `python run.py` 自动启动服务、执行 pytest、输出 Allure 原始结果和 JUnit XML |
| 仪器数据采集与信号输出 | `DAS-001` 仿真设备下发采集参数；真实 TDMS 波形计算均值、RMS、峰值 |
| 预警与异常筛查 | RMS 阈值告警；连续通道背景学习、鲁棒 Z 分数、局部 RMS 比初筛 |
| 测试文档沉淀 | 本 README 的测试范围、边界和面试表述；Allure/JUnit 作为执行报告 |

## 必须如实说明的边界

- `DAS-001` 是本地仿真设备，不是实习公司的真实仪器或线上系统。
- TDMS 元数据和信号质量指标来自真实数据；采集任务状态是为了练习接口工作流而建立的内存仿真。
- MATLAB 自动背景预警 App 的输入是 PhaseOTDR 二进制数据；本服务对 TDMS 实现的是单文件背景初筛，不等价于其跨文件红橙黄最终预警。
- 真实软硬件联调、Linux 日志分析、外场试验属于你的实际实习经历，但不能由这个本地接口工程替代或伪造。

## 接口与测试链路

```text
设备状态 → 查询 TDMS 文件 → 下发采集任务 → 查询任务
                              ↓
                  信号 RMS/峰值检查 → 告警评价
                              ↓
                       自动背景异常初筛
```

| 接口 | 业务目的 | 关键测试点 |
| --- | --- | --- |
| `GET /api/v1/devices/{id}/status` | 采集前设备状态检查 | 在线状态、设备不存在 |
| `GET /api/v1/tdms/files` | 查询真实采集源文件 | 小时参数、文件列表 |
| `POST /api/v1/acquisition/tasks` | 下发采集任务 | 采样率、通道范围、采集时长 |
| `GET /api/v1/acquisition/tasks/{id}` | 查询采集结果 | 任务关联、任务不存在 |
| `POST /api/v1/tdms/quality-check` | 检查信号输出质量 | RMS、峰值、通道/时间窗边界 |
| `POST /api/v1/signals/alarms/evaluate` | 预警分级 | 正常/预警/告警阈值 |
| `POST /api/v1/warnings/background-scan` | 自动背景异常初筛 | 背景池比例、连续通道、参数边界 |

## 目录

```text
base/        请求发送、YAML 解析、断言、变量提取（extract.yaml）
common/      路径与配置工具
conf/        服务和 TDMS 数据根目录配置
data/        预留给独立测试数据；真实原始数据不复制进仓库
testcase/    YAML 业务链路、异常/边界/性能 pytest 用例
report/      Allure 原始结果、JUnit XML
mock_server/ 本地 DAS 仪器监测服务
```

## Windows 运行

```powershell
cd D:\pytest_practice\tdms_api_interview_demo
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

成功标准：pytest 通过 4 条测试（1 条业务回归链路、2 条异常/边界、1 条性能冒烟），并生成 `report/junit.xml` 与 `report/allure-results`。

若数据根目录不同，修改 [config.yaml](D:\pytest_practice\tdms_api_interview_demo\conf\config.yaml) 的 `tdms.data_root`。运行后 `base/extract.yaml` 会记录当前业务链路提取到的文件路径、任务 ID、RMS；该文件已被 Git 忽略。

如已安装 Allure CLI：

```powershell
allure serve report\allure-results
```

## VS Code + Git

仓库已初始化但未创建提交。打开项目目录后，在 Source Control 面板查看变更、暂存并提交；或执行：

```powershell
git add .
git commit -m "feat: add DAS instrument API automation practice"
git log --oneline
```

## 两小时学习顺序

1. 运行 `python run.py`，查看 4 条 pytest 结果和 `extract.yaml`。
2. 从 [01_login.yaml](D:\pytest_practice\tdms_api_interview_demo\testcase\cases\01_login.yaml) 开始，顺序阅读 7 个 YAML 用例，理解文件路径、任务 ID、RMS 如何关联。
3. 阅读 [app.py](D:\pytest_practice\tdms_api_interview_demo\mock_server\app.py)，重点看采集参数校验、质量检查和背景初筛。
4. 把 `sampling_rate_hz` 改为 `500`，运行异常用例，观察 422 响应与报告；随后还原。
5. 在 VS Code 暂存、提交，并准备下方回答。

## 面试回答（如实）

“我基于仪器测试业务抽象搭建了一个本地 DAS 监测服务，用 pytest、requests 和 YAML 做接口自动化。正常链路覆盖设备状态、采集任务下发与查询、真实 TDMS 信号的 RMS/峰值质量检查、阈值告警和背景初筛；文件路径、任务 ID、RMS 通过 extract.yaml 实现接口关联。异常侧覆盖不支持采样率和超范围通道，性能侧对指定时间窗的信号质量检查设置了 2 秒冒烟阈值。服务不改写原始 TDMS 数据，Allure 与 JUnit 记录回归结果。这个项目是对实习测试流程的本地抽象复现；实际实习还包含真实仪器联调、日志分析和现场试验。”
