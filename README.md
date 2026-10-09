# 鱼类三维行为分析系统

本项目分阶段复现论文的单摄像机与平面镜鱼类行为分析路线。
当前已完成 S0/S1 的三维轨迹数据合同与合成轨迹运动分析，S2 的视频读取、
去畸变接口、中值滤波、HSV 转换和双视角分区，以及 S3 的 LBAdaptiveSOM 前景分割。尚未接入真实实验视频，
也未验证真实三维重建或行为识别准确率。

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
.\.venv\Scripts\python -m fish3d video-demo --config configs/synthetic_video.yaml --output outputs/synthetic_video_demo
.\.venv\Scripts\python -m fish3d som-demo --config configs/synthetic_som.yaml --output outputs/synthetic_som_demo
```

第一个示例输出标记 `synthetic` 的轨迹 CSV、三张图和运行记录。第二个示例
生成带 `SYNTHETIC` 字样的 AVI，并保存逐帧图像、原始 OpenCV HSV 数组、
双视角 ROI、时间戳表和运行记录。第三个示例用前三帧无鱼背景初始化 SOM，
输出双视角及全帧前景掩膜、叠加图、背景模型和分割记录。已有视频可用以下入口处理：

```powershell
.\.venv\Scripts\python -m fish3d preprocess-video --input path\to\video.avi --config configs/synthetic_video.yaml --output outputs/my_run
.\.venv\Scripts\python -m fish3d segment-video --input outputs/synthetic_som_demo/synthetic_input.avi --config configs/synthetic_som.yaml --output outputs/my_som_run
```

处理真实视频时须使用另行测定 ROI、尺寸、时间和标定参数的配置文件，并将
`data_source` 改为 `experimental`。`outputs/` 不提交到 Git。字段与 S2
文件格式见 `docs/data_contract.md` 和 `docs/video_preprocessing.md`。
SOM 数值范围、论文公式歧义、参数来源及已知限制见 `docs/lbadaptive_som.md`。
视频尺寸和 ROI 必须与配置一致；S3 示例参数仅供 synthetic 验证。

## 开发阶段

S0 工程结构和数据接口；S1 合成轨迹、运动特征与图表；S2 视频预处理（已完成 synthetic 验证）；
S3 LBAdaptiveSOM（已完成 synthetic 验证）；S4 质心与跟踪；S5 双视角匹配和三维重建；
S6 行为识别；S7 真实实验视频验证。进入 S4 需用户确认。

