# 鱼类三维行为分析系统

本项目分阶段复现论文的单摄像机与平面镜鱼类行为分析路线。
当前阶段 S0/S1 仅提供三维轨迹数据合同与合成轨迹的运动分析，
尚未接入真实视频，也未验证真实三维重建或行为识别准确率。

## 安装

在 Windows PowerShell 和 Python 3.11 环境中：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -e '.[test]'
```

## 验证与运行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
.\.venv\Scripts\python -m fish3d simulate --config configs/default.yaml --output outputs/synthetic_demo
```

示例输出为标记 `synthetic` 的 CSV、三维轨迹图、速度图、角速度图和
`run_manifest.json`。`outputs/` 不提交到 Git。输入配置见 `configs/default.yaml`；
字段和未来模块接口见 `docs/data_contract.md`。

## 开发阶段

S0 工程结构和数据接口；S1 合成轨迹、运动特征与图表；S2 视频预处理；
S3 LBAdaptiveSOM；S4 质心与跟踪；S5 双视角匹配和三维重建；
S6 行为识别；S7 真实实验视频验证。进入 S2 需用户确认。

