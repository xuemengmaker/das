# 学习与 Git/GitHub 操作清单

本清单只围绕“仪器测试开发实习的软件自动化部分”，不把本地仿真项目说成原公司生产系统。

## 回来后两小时安排

| 时间 | 目标 | 你实际要做的事 |
| --- | --- | --- |
| 0-15 分钟 | 启动项目 | 在 VS Code 打开项目，运行 `./start_service.ps1`，确认 Flask 服务地址为 `127.0.0.1:5000` |
| 15-45 分钟 | 手工接口调试 | 导入 Postman 集合，按 01-07 顺序点击 Send，观察变量 `tdms_file`、`task_id`、`channel_1_rms` |
| 45-75 分钟 | 自动化回归 | 运行 `./run_tests.ps1`，理解 1 条业务链路、2 条异常/边界、1 条性能冒烟测试 |
| 75-100 分钟 | 改一条用例 | 将采样率改为 500，解释为何应返回 422；再还原并确认回归通过 |
| 100-120 分钟 | Git 与面试表达 | 在 VS Code 暂存、提交；用 README 的一分钟回答复述项目 |

## Postman 准备

1. 在 Postman 点击 **Import**。
2. 选择 `data/DAS_Instrument_API.postman_collection.json`。
3. 先运行 `start_service.ps1`，不要关闭服务终端。
4. 在 Collection 中按编号 01 到 07 顺序发送。02、03、05 会保存集合变量，后续请求依赖这些变量。

## Git 操作

在项目根目录运行：

```powershell
git status
git add .
git commit -m "feat: add DAS instrument API automation practice"
git log --oneline
```

不要提交：`.venv/`、`report/allure-results/`、`report/junit.xml`、`base/extract.yaml` 和任何真实 TDMS 文件。`.gitignore` 已处理这些路径。

## 上传 GitHub（你回来后确认再做）

1. 在 GitHub 网页创建一个空仓库，不要勾选 README、`.gitignore` 或 License。
2. 将网页显示的仓库地址替换到以下命令：

```powershell
git branch -M main
git remote add origin https://github.com/你的账号/das-instrument-api-practice.git
git push -u origin main
```

上传前再次执行 `git status`，确认没有 `F:\数据`、个人路径、报告运行结果或密钥。GitHub 仓库建议设为 Private，之后再决定是否公开。

## 面试必答

- **测试了什么？** 设备状态、采集参数、采集任务关联、TDMS 信号 RMS/峰值、告警和背景初筛。
- **异常/边界？** 不支持采样率、通道越界、采样窗约束、阈值关系错误。
- **如何接口关联？** YAML 从文件查询提取路径，再提取任务 ID 与 RMS，写入 `extract.yaml` 供下游接口使用。
- **性能怎么测？** 对 1,000 样点、2 通道质量检查做 2 秒性能冒烟；不是高并发压测。
- **最大边界？** 本地服务和仿真设备是练习环境，真实 TDMS 数据只读；实习现场硬件联调不能由此替代。
