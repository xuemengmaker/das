"""本地 TDMS 数据服务：仅读取真实数据的目录与元数据，不读取完整波形。"""
import os
import re
from itertools import count
from pathlib import Path

from flask import Flask, jsonify, request
import numpy as np
from nptdms import TdmsFile


DEFAULT_DATA_ROOT = Path(r"F:\数据")


def _safe_file(data_root: Path, relative_path: str) -> Path:
    """只允许访问数据根目录内的 .tdms 文件，避免路径穿越。"""
    candidate = (data_root / relative_path).resolve()
    if data_root not in candidate.parents or candidate.suffix.lower() != ".tdms":
        raise ValueError("只允许访问数据根目录内的 .tdms 文件")
    return candidate


def _metadata(file_path: Path) -> dict:
    """读取真实 TDMS 元数据；不加载 1.9 GB 波形数据。"""
    tdms = TdmsFile.read_metadata(file_path)
    channels = [channel for group in tdms.groups() for channel in group.channels()]
    if len(channels) != 1:
        raise ValueError(f"期望一个扁平数据通道，实际为 {len(channels)} 个")
    properties = dict(tdms.properties)
    channel_count = int(properties["channels"])
    sample_count = int(properties["samples"])
    sampling_rate_hz = float(properties["sample_ratio"])
    if len(channels[0]) != channel_count * sample_count:
        raise ValueError("TDMS 元数据与通道长度不一致")
    return {
        "relative_path": file_path.relative_to(file_path.parents[1]).as_posix(),
        "bytes": file_path.stat().st_size,
        "n_channels": channel_count,
        "n_samples": sample_count,
        "sampling_rate_hz": sampling_rate_hz,
        "group": tdms.groups()[0].name,
        "channel": channels[0].name,
    }


def _quality_check(file_path: Path, channels_one_based: list[int], start_sample: int, n_samples: int) -> dict:
    """读取小时间窗的真实波形，计算可用于冒烟检查的基础信号指标。"""
    meta = _metadata(file_path)
    total_channels = meta["n_channels"]
    total_samples = meta["n_samples"]
    if not channels_one_based or len(channels_one_based) > 8:
        raise ValueError("channels_one_based 必须包含 1-8 个通道号")
    if any(not isinstance(item, int) or item < 1 or item > total_channels for item in channels_one_based):
        raise ValueError(f"通道号必须在 1-{total_channels} 范围内")
    if not 0 <= start_sample < total_samples or not 1 <= n_samples <= 2000 or start_sample + n_samples > total_samples:
        raise ValueError(f"采样窗必须位于 0-{total_samples - 1} 内，且长度为 1-2000")

    with TdmsFile.open(file_path) as tdms:
        channel = tdms[meta["group"]][meta["channel"]]
        flat = channel.read_data(offset=start_sample * total_channels, length=n_samples * total_channels)
    data = flat.reshape(n_samples, total_channels).T[np.asarray(channels_one_based) - 1]
    metrics = [
        {
            "channel": channel_no,
            "mean": float(np.mean(trace)),
            "rms": float(np.sqrt(np.mean(np.square(trace)))),
            "peak_abs": float(np.max(np.abs(trace))),
        }
        for channel_no, trace in zip(channels_one_based, data, strict=True)
    ]
    return {
        "relative_path": meta["relative_path"],
        "window": {"start_sample": start_sample, "n_samples": n_samples, "channel_count": len(metrics)},
        "metrics": metrics,
    }


def _background_scan(file_path: Path, channel_start: int, channel_end: int, start_sample: int, n_samples: int, background_fraction: float) -> dict:
    """TDMS 单文件背景学习初筛，复用预警 App 的 RMS/MAD/局部比思路。"""
    meta = _metadata(file_path)
    total_channels = meta["n_channels"]
    if not 1 <= channel_start <= channel_end <= total_channels or channel_end - channel_start + 1 > 64:
        raise ValueError(f"通道范围必须在 1-{total_channels} 内，且一次最多扫描 64 道")
    if not 0 <= start_sample < meta["n_samples"] or not 100 <= n_samples <= 2000 or start_sample + n_samples > meta["n_samples"]:
        raise ValueError("采样窗必须位于文件范围内，长度为 100-2000")
    if not 0.5 <= background_fraction <= 0.8:
        raise ValueError("background_fraction 必须为 0.50-0.80")

    channel_ids = np.arange(channel_start, channel_end + 1)
    with TdmsFile.open(file_path) as tdms:
        channel = tdms[meta["group"]][meta["channel"]]
        flat = channel.read_data(offset=start_sample * total_channels, length=n_samples * total_channels)
    signals = flat.reshape(n_samples, total_channels).T[channel_ids - 1]
    rms_values = np.sqrt(np.mean(np.square(signals), axis=1))
    median_rms = float(np.median(rms_values))
    robust_scale = max(float(1.4826 * np.median(np.abs(rms_values - median_rms))), 1e-12)
    rms_z = (rms_values - median_rms) / robust_scale
    local_medians = np.array([
        np.median(rms_values[max(0, index - 2): min(len(rms_values), index + 3)])
        for index in range(len(rms_values))
    ])
    local_ratio = rms_values / np.maximum(local_medians, 1e-12)
    quiet_score = np.maximum(rms_z, 0.0) + np.maximum(local_ratio - 1.0, 0.0)
    background_count = max(4, round(len(channel_ids) * background_fraction))
    background_indexes = np.argsort(quiet_score)[:background_count]
    candidate_indexes = np.where((rms_z >= 2.0) & (local_ratio >= 1.20))[0]
    return {
        "analysis_scope": "single_file_preliminary_screening",
        "limitation": "不包含跨文件/跨时间持续性，不能替代 MATLAB App 的红橙黄最终预警。",
        "relative_path": meta["relative_path"],
        "window": {"start_sample": start_sample, "n_samples": n_samples, "channel_count": len(channel_ids)},
        "background": {"fraction": background_fraction, "channel_count": background_count, "channels": channel_ids[background_indexes].tolist()},
        "candidates": [
            {"channel": int(channel_ids[index]), "rms": float(rms_values[index]), "rms_z": float(rms_z[index]), "local_rms_ratio": float(local_ratio[index])}
            for index in candidate_indexes
        ],
    }


def create_app(data_root: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    root = Path(data_root or os.getenv("TDMS_DATA_ROOT", DEFAULT_DATA_ROOT)).resolve()
    devices = {
        "DAS-001": {
            "device_id": "DAS-001",
            "model": "distributed-fiber-sensing-emulator",
            "status": "online",
            "supported_sample_rates_hz": [1000],
            "max_channels": 4000,
            "acquisition_supported": True,
        }
    }
    acquisition_tasks: dict[str, dict] = {}
    task_counter = count(1)

    @app.get("/api/v1/devices/<device_id>/status")
    def device_status(device_id: str):
        device = devices.get(device_id)
        if not device:
            return jsonify(code=4004, message="设备不存在", data={}), 404
        return jsonify(code=0, message="设备状态查询成功", data=device)

    @app.get("/api/v1/tdms/files")
    def list_files():
        hour = request.args.get("hour", "")
        if not re.fullmatch(r"(?:[01]\d|2[0-3])", hour):
            return jsonify(code=4001, message="hour 必须是 00-23", data={}), 400
        hour_dir = root / hour
        if not hour_dir.is_dir():
            return jsonify(code=4004, message="小时目录不存在", data={}), 404
        limit = min(max(int(request.args.get("limit", 10)), 1), 50)
        files = sorted(hour_dir.glob("*.tdms"))[:limit]
        return jsonify(code=0, message="查询成功", data={
            "hour": hour,
            "count": len(files),
            "files": [{"relative_path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size} for path in files],
        })

    @app.post("/api/v1/acquisition/tasks")
    def start_acquisition():
        """仿真仪器采集任务下发，任务引用真实 TDMS 文件作为只读采集结果。"""
        body = request.get_json(silent=True) or {}
        device = devices.get(body.get("device_id"))
        if not device:
            return jsonify(code=4004, message="设备不存在", data={}), 404
        if device["status"] != "online":
            return jsonify(code=4091, message="设备不在线，不能下发采集任务", data={}), 409
        try:
            sampling_rate = int(body["sampling_rate_hz"])
            channel_start = int(body["channel_start"])
            channel_end = int(body["channel_end"])
            duration_seconds = int(body["duration_seconds"])
            source_file = _safe_file(root, body["source_file"])
            if sampling_rate not in device["supported_sample_rates_hz"]:
                raise ValueError(f"设备不支持 {sampling_rate} Hz 采样率")
            if not 1 <= channel_start <= channel_end <= device["max_channels"]:
                raise ValueError(f"通道范围必须位于 1-{device['max_channels']}")
            if not 1 <= duration_seconds <= 60:
                raise ValueError("采集时长必须为 1-60 秒")
            if not source_file.is_file():
                return jsonify(code=4004, message="采集源 TDMS 文件不存在", data={}), 404
        except (KeyError, TypeError, ValueError) as error:
            return jsonify(code=4223, message=f"采集参数异常：{error}", data={}), 422

        task_id = f"ACQ-{next(task_counter):04d}"
        task = {
            "task_id": task_id,
            "device_id": device["device_id"],
            "status": "completed",
            "sampling_rate_hz": sampling_rate,
            "duration_seconds": duration_seconds,
            "channel_start": channel_start,
            "channel_end": channel_end,
            "output": {
                "relative_path": source_file.relative_to(root).as_posix(),
                "samples_per_channel": sampling_rate * duration_seconds,
            },
        }
        acquisition_tasks[task_id] = task
        return jsonify(code=0, message="采集任务完成", data=task), 201

    @app.get("/api/v1/acquisition/tasks/<task_id>")
    def get_acquisition_task(task_id: str):
        task = acquisition_tasks.get(task_id)
        if not task:
            return jsonify(code=4004, message="采集任务不存在", data={}), 404
        return jsonify(code=0, message="采集任务查询成功", data=task)

    @app.post("/api/v1/tdms/quality-check")
    def quality_check():
        body = request.get_json(silent=True) or {}
        try:
            file_path = _safe_file(root, body.get("relative_path", ""))
            if not file_path.is_file():
                return jsonify(code=4004, message="TDMS 文件不存在", data={}), 404
            result = _quality_check(
                file_path,
                body.get("channels_one_based", []),
                body.get("start_sample", 0),
                body.get("n_samples", 1000),
            )
            return jsonify(code=0, message="质量检查完成", data=result)
        except (KeyError, TypeError, ValueError, OSError) as error:
            return jsonify(code=4222, message=f"质量检查参数或数据异常：{error}", data={}), 422

    @app.post("/api/v1/signals/alarms/evaluate")
    def evaluate_alarm():
        """根据接口上传的 RMS 评价信号输出级别，覆盖正常/预警/告警边界。"""
        body = request.get_json(silent=True) or {}
        try:
            rms = float(body["rms"])
            warning = float(body["warning_threshold"])
            critical = float(body["critical_threshold"])
            if rms < 0 or warning <= 0 or critical <= warning:
                raise ValueError("阈值必须满足 0 < warning < critical，且 RMS 不能为负")
        except (KeyError, TypeError, ValueError) as error:
            return jsonify(code=4224, message=f"告警参数异常：{error}", data={}), 422
        severity = "critical" if rms >= critical else "warning" if rms >= warning else "normal"
        return jsonify(code=0, message="告警评价完成", data={
            "rms": rms,
            "warning_threshold": warning,
            "critical_threshold": critical,
            "severity": severity,
        })

    @app.post("/api/v1/warnings/background-scan")
    def background_scan():
        """自动背景学习的单文件初筛接口，面向预警 App 的业务流程练习。"""
        body = request.get_json(silent=True) or {}
        try:
            file_path = _safe_file(root, body.get("relative_path", ""))
            if not file_path.is_file():
                return jsonify(code=4004, message="TDMS 文件不存在", data={}), 404
            result = _background_scan(
                file_path,
                int(body["channel_start"]),
                int(body["channel_end"]),
                int(body.get("start_sample", 0)),
                int(body.get("n_samples", 1000)),
                float(body.get("background_fraction", 0.60)),
            )
            return jsonify(code=0, message="背景初筛完成", data=result)
        except (KeyError, TypeError, ValueError, OSError) as error:
            return jsonify(code=4225, message=f"背景初筛参数或数据异常：{error}", data={}), 422

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
