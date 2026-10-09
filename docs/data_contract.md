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
视频读取与预处理在 S2 已实现；分割、质心、跟踪、匹配和重建仍为接口合同。

论文理想模型 `z=(a-x')tan(α)` 的输出是模型坐标；在取得装置几何、
相机标定和尺度验证之前，不把它标为真实世界高度。论文的 640×480、
45°、285/355 分区均属于既往实验设置，不是本实验已测参数。

## S2 数据需求

实验人员后续提供原始视频、逐帧时间戳或帧率、相机标定文件、镜面角度和位置、
鱼缸尺度及双视角 ROI 的参考画面。算法侧负责读取和校验这些数据。

