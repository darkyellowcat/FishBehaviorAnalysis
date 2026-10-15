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

## 多鱼二维预览合同

最终需求包含多鱼；experiment_001 已确认 5 条，EVE2/EVE3 已确认各 3 条，数量按视频配置。
原视频左侧黑底是实体、右侧是镜像，新增视频方向按抽帧判断。
`extract_all` 返回通过面积及可选形状门限的连通域，默认不启用形状限制，原 `extract` 的最大目标语义保持不变。
`MultiFishTracker` 在原 Detection2D/TrackedDetection 之外附加状态，不修改核心接口。

多鱼 `detections.csv` 同一帧同一视角可以有多行，保留候选索引和未分配状态；
`tracks_2d.csv` 用 `(frame_id, view, fish_id)` 区分轨迹观测，同帧可以有多个编号。
已有轨迹缺失、疑似合并遮挡或丢失时坐标均为 NaN，面积为 0，不导出预测位置。
尚无轨迹的帧只在 frames.csv 中记录计数，不能因已知鱼数补写虚构目标。

分割掩膜为缩放 ROI 局部像素；检测/轨迹输出质心换回原尺度 processed_full_frame / px。
输出 area_px 为近似原尺度等效面积，配置面积筛选在缩放掩膜上进行，详见 `multi_fish_tracking.md`。
这是独立二维预览入口，旧 S5/S6 单鱼 CSV 入口尚不接收同帧多鱼记录；
视角内编号不表示跨视角对应或经验证的物理鱼身份。

多鱼预览增加 `components.csv`，保存形状筛选前全部面积合格组件的局部缩放质心、
面积、主次轴比及是否通过形状筛选；不是三维坐标或人工鱼标签。
frames.csv 另记 area_candidate_count、shape_rejected_count 和 tentative_candidate_count。
原 `candidate_count` 与 detections.csv 均表示形状筛选后的候选；默认关闭时与原定义相同。
`cleaned_masks/` 仍是形态学后的全部前景，不因形状拒绝而删除像素。

`birth_confirmation_frames` 默认 1，保持旧跟踪行为；配置为 3 时新候选先输出到检测表，
状态为 tentative，连续三帧观测确认后才分配正式编号并写轨迹表。
不把前两帧或预测点回填为正式轨迹。未确认候选不占已确认鱼数容量，
错失/跳帧会中断其连续确认；已确认轨迹的缺失、NaN 和长失踪语义不变。

