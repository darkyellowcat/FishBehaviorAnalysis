# 鱼类三维行为分析系统

本项目分阶段复现论文的单摄像机与平面镜鱼类行为分析路线。
当前已完成 S0/S1 的三维轨迹数据合同与合成轨迹运动分析，S2 的视频读取、
去畸变接口、中值滤波、HSV 转换和双视角分区，S3 的 LBAdaptiveSOM 前景分割，
S4 的单鱼质心提取与二维时间跟踪、S5 的单鱼双视角对应与论文理想像素模型重建，
以及 S6 的三类规则行为识别、CSV 接入和图表导出。
尚未接入真实实验视频，
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
.\.venv\Scripts\python -m fish3d tracking-demo --config configs/synthetic_tracking.yaml --output outputs/synthetic_tracking_demo
.\.venv\Scripts\python -m fish3d geometry-demo --config configs/synthetic_geometry.yaml --output outputs/synthetic_geometry_demo
.\.venv\Scripts\python -m fish3d behavior-demo --config configs/synthetic_behavior.yaml --output outputs/synthetic_behavior_demo
```

第一个示例输出标记 `synthetic` 的轨迹 CSV、三张图和运行记录。第二个示例
生成带 `SYNTHETIC` 字样的 AVI，并保存逐帧图像、原始 OpenCV HSV 数组、
双视角 ROI、时间戳表和运行记录。第三个示例用前三帧无鱼背景初始化 SOM，
输出双视角及全帧前景掩膜、叠加图、背景模型和分割记录。第四个示例增加两帧
合成鱼消失，保存质心表、二维跟踪表、清理掩膜及轨迹图。第五个示例继续匹配两视角，
输出匹配记录及 `model_px` 单位的三维轨迹，保留无效帧。已有数据可用以下入口处理：

```powershell
.\.venv\Scripts\python -m fish3d preprocess-video --input path\to\video.avi --config configs/synthetic_video.yaml --output outputs/my_run
.\.venv\Scripts\python -m fish3d segment-video --input outputs/synthetic_som_demo/synthetic_input.avi --config configs/synthetic_som.yaml --output outputs/my_som_run
.\.venv\Scripts\python -m fish3d track-video --input outputs/synthetic_tracking_demo/synthetic_input.avi --config configs/synthetic_tracking.yaml --output outputs/my_tracking_run
.\.venv\Scripts\python -m fish3d reconstruct-tracks --input outputs/synthetic_tracking_demo/tracks_2d.csv --config configs/synthetic_geometry.yaml --output outputs/my_geometry_run
.\.venv\Scripts\python -m fish3d analyze-behavior --input outputs/synthetic_geometry_demo/trajectory_3d.csv --config configs/synthetic_behavior_model.yaml --output outputs/synthetic_behavior_video_replay
```

处理真实视频时须使用另行测定 ROI、尺寸、时间和标定参数的配置文件，并将
`data_source` 改为 `experimental`。`outputs/` 不提交到 Git。字段与 S2
文件格式见 `docs/data_contract.md` 和 `docs/video_preprocessing.md`。
SOM 数值范围、论文公式歧义、参数来源及已知限制见 `docs/lbadaptive_som.md`。
质心筛选、时间关联、无效标记和真实视频适配需求见 `docs/centroid_tracking.md`。
S5 几何公式、坐标与单位、对应假设和物理标定需求见 `docs/geometry_reconstruction.md`。
理想模型不会仅凭相机内参自动获得物理尺度，不允许将输出配置为毫米。
S6 规则、事件时间边界、单位、来源保护、输出和真实标签需求见 `docs/behavior_analysis.md`。
行为示例从配置构造 51 个 synthetic 坐标，计算狂游、持续漂浮与跳出规则预测；
缺失或未知特征不当作正常，阈值须在真实数据取得后重新确认。
视频尺寸和 ROI 必须与配置一致；示例参数仅供 synthetic 验证。

## 开发阶段

S0 工程结构和数据接口；S1 合成轨迹、运动特征与图表；S2 视频预处理（已完成 synthetic 验证）；
S3 LBAdaptiveSOM（已完成 synthetic 验证）；S4 质心与跟踪（已完成 synthetic 验证）；
S5 双视角匹配和三维重建（已完成 synthetic 理想模型验证）；S6 行为识别与可视化（已完成 synthetic 规则验证）；
S7 真实实验视频验证。进入 S7 需用户确认并取得真实实验资料。

