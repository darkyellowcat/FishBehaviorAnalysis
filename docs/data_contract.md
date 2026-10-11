# 数据合同与来源

S0/S1 计算人工构造的三维轨迹，`data_source=synthetic`。默认坐标系为
`synthetic_cartesian`，单位为 `synthetic_unit`，不代表相机像素或物理毫米。

每条 `TrajectoryPoint` 包含 `frame_id`、`timestamp_s`、`fish_id`、`X`、`Y`、
`Z`、`coordinate_unit`、`is_valid`、`coordinate_frame`、`data_source`。
同一条轨迹只允许一个鱼 ID、单位、坐标系与来源；帧号和时间戳必须严格递增。
无效点的三个坐标均为 NaN；有效点的三个坐标均为有限数。

`interfaces.py` 定义视频、预处理及后续前景分割、质心、跟踪、双视角匹配、
重建和行为模块的输入输出。`ViewFrame` 与 `ForegroundMask` 携带 ROI 原点；
`Detection2D` 使用全帧像素坐标与 `real`/`mirror` 视角标签。转换责任在质心
提取模块。跟踪结果附带鱼 ID，匹配模块核对两视角对应关系；
`Reconstructor` 将两个同帧、同时间戳的匹配检测转成带坐标系和单位的轨迹点。
视频读取、预处理、LBAdaptiveSOM 前景分割、单鱼质心与二维时间跟踪已实现；
S5 已实现单鱼双视角对应及论文理想像素模型重建，实际物理重建尚未验证。
前景掩膜保留同帧时间戳与 ROI 原点，像素值为 0（背景或阴影）及 255（前景）。

S4 检测与跟踪表每帧各视角均有一行。缺失/被拒绝的跟踪坐标为 NaN、面积为 0、
is_valid=false；跟踪前的有效原始检测可以在关联时被拒绝。
图像坐标系为 `processed_full_frame`、单位 px；去畸变启用时与原始像素坐标有别。
fish_id 是视角内轨迹段编号，尚未确认两视角或物理身份；首点出现前或长失踪后
无编号时为空字符串。状态、关联规则及结果格式见 `centroid_tracking.md`。

S5 输入沿用 S4 完整图像 px 坐标；输出为 `paper_ideal_cartesian` 与 `model_px`，
不代表鱼缸世界坐标或毫米尺度。成功配对后的 fish_id 由两视角轨迹段编号组成；
首次成功前为 `unassigned`。三维 CSV 可能含多个配对段，使用单鱼运动接口前
须按编号分组。匹配失败时三维坐标全部为 NaN，保留该帧与来源。
几何参考位置独立于 ROI 分区，详细规则、标定入口与数据需求见 `geometry_reconstruction.md`。

论文理想模型 `z=(a-x')tan(α)` 的输出是模型坐标；在取得装置几何、
相机标定和尺度验证之前，不把它标为真实世界高度。论文的 640×480、
45°、285/355 分区均属于既往实验设置，不是本实验已测参数。

## S2 数据需求

实验人员后续提供原始视频、逐帧时间戳或帧率、相机标定文件、镜面角度和位置、
鱼缸尺度及双视角 ROI 的参考画面。算法侧负责读取和校验这些数据。

## S6 行为与运动结果

S6 接收 S1/S5 单鱼 CSV，允许配对段编号变化，每帧一行；来源、坐标系与单位
逐条匹配规则配置。先按连续有效观测分段，再复用 S1 计算，不跨缺失、编号变化、
漏帧或过大的时间间隔求差分。同编号累计路径只包含实际观测到的相邻三维步长。

`RuleBehaviorRecognizer` 实现既有 `BehaviorRecognizer.detect`，仍返回 `BehaviorEvent`。
事件区间表示连续规则成立的观测时刻，漂浮从首次超过持续时间阈值的点开始；
不把尚未达到阈值的水面接触段回填为已检出行为。

`behavior_samples.csv` 保留全部帧，携带三项规则布尔标记、水面持续时间、
is_valid 和 frantic_evaluable。无效/未知帧的 false 是未检出，不能当作确认正常。
`behavior_events.csv` 附来源、单位、坐标系及 `result_type=rule_prediction`；
不包含无真实标签支持的识别准确率。所有阈值单位及起止边界详见 `behavior_analysis.md`。

