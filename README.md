# 鱼类三维行为分析系统

本项目分阶段复现论文的单摄像机与平面镜鱼类行为分析路线。
当前已完成 S0/S1 的三维轨迹数据合同与合成轨迹运动分析，S2 的视频读取、
去畸变接口、中值滤波、HSV 转换和双视角分区，S3 的 LBAdaptiveSOM 前景分割，
S4 的单鱼质心提取与二维时间跟踪、S5 的单鱼双视角对应与论文理想像素模型重建，
以及 S6 的三类规则行为识别、CSV 接入和图表导出。
已进行真实实验视频的短片段二维接入预览，
尚未完成真实全片、三维重建或行为识别准确率验证。

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

## 多鱼需求与真实视频接入预览

最终要求为多鱼。experiment_001 经用户确认有 5 条鱼，左侧黑底为实体视角，右侧为镜像。
用户后续确认 EVE2、EVE3 各有 3 条鱼（两条损耗），数量按各视频独立配置。
新增全部候选质心和多目标二维关联入口，保留原单鱼示例与命令。
实体视角配置、关联算法、缩放/缺失合同及限制见 `docs/multi_fish_tracking.md`。

```powershell
.\.venv\Scripts\python -m fish3d multi-tracking-demo --config configs/synthetic_multi_tracking.yaml --output outputs/synthetic_multi_tracking_demo
.\.venv\Scripts\python -m fish3d track-multi-video --input data/raw/experiment_001.mp4 --config configs/experiment_001_multi_preview.yaml --output outputs/experiment_001_multi_preview
```

第二条仅处理实体视角前 60 帧，ROI 由画面初步估计、尚待确认；0.25 尺度分割后恢复原尺度坐标。
已知五鱼不强制每帧检出五条，编号仅为视角内轨迹段。多鱼跨视角匹配、三维重建与行为入口
尚未适配完成，不能直接把该多行二维 CSV 输入原单鱼重建命令；完整真实视频验证尚未完成。

2026-10-15 新增 EVE2/EVE3 两份 2448×2048 视频的独立配置及可重复对照。
连续观测确认可减少短暂候选直接产生的正式编号；形状筛选在真实数据上使轨迹更碎，
保留为实验选项，默认关闭。两者均保留论文 SOM，不能据段数减少宣称身份准确率提高。

```powershell
.\.venv\Scripts\python -m fish3d track-multi-video --input data/raw/VIDEO_20261014_EVE2.mp4 --config configs/eve2_multi_confirmed.yaml --output outputs/eve2_confirmed
```

新增视频的三个配置变体均已修正为 3 条鱼；左右映射仍按抽帧判断，ROI 未经标定确认。
此前使用五鱼容量的试跑是历史诊断，不是三鱼条件下的验收结果。
圈图反馈放在 `data/annotations/`，例如 `eve2_frame_000059_marked.jpg`，该目录不上传 Git。
人工反馈图、标注约定及交给实验人员的视频要求见 `docs/video_feedback.md`。

## 开发阶段

S0 工程结构和数据接口；S1 合成轨迹、运动特征与图表；S2 视频预处理（已完成 synthetic 验证）；
S3 LBAdaptiveSOM（已完成 synthetic 验证）；S4 质心与跟踪（已完成 synthetic 验证）；
S5 双视角匹配和三维重建（已完成 synthetic 理想模型验证）；S6 行为识别与可视化（已完成 synthetic 规则验证）；
S7 真实实验视频验证。进入 S7 需用户确认并取得真实实验资料。

