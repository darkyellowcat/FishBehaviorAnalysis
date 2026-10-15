# 多鱼需求与二维接入预览

## 已确认的实验信息与本轮范围

用户于 2026-10-15 明确：最初 **5 条鱼**，损耗 **1 条**后为 **4 条**，从未有过三条的阶段。
experiment_001 按最初五条配置；EVE2/EVE3 以及本次新增的 a3d72…_raw/a8d940… 视频按后续四条记录。
此前三条及“始终四条”的记录均已纠正；损耗发生时刻未知，不推断视频内具体转变帧。
左侧黑底为实体视角，右侧为镜像。论文的“左镜像、右实体”及其像素参数不能直接套用。
已将 `experiment_001.mp4` 的实体 ROI 配置在左侧，来源设置为 experimental。
960×800、报告帧率 10 fps 来自视频；矩形 ROI 是抽帧估计，尚非标定结果。

本轮完成全部连通域质心提取、多目标二维关联及实体视角的限长预览。
保留原论文 LBAdaptiveSOM，不用深度学习或其他分割器替代。
旧单鱼 S4–S6 命令保持原有行为，本轮不把它们包装为多鱼三维系统。
尚待完成多鱼跨视角对应、每条鱼三维重建和行为数据接入，以及真实数据评价。

## 方法和接口

- `ConnectedComponentCentroidExtractor.extract_all`：返回全部满足面积门限的连通域，
  按面积降序、质心 y/x 排序。复用原形态学和质心计算；`extract` 仍取第一项，保持单鱼兼容。
- `MultiFishTracker.update(frame_id, timestamp_s, detections)`：接收同一帧同一视角的多个有效检测，
  返回携带原 `TrackedDetection` 的 `MultiTrackObservation` 和状态，不修改核心数据合同。
- 空候选帧也必须调用 update。仅已有轨迹有缺失记录，初始化时不生成不存在的鱼坐标或身份。
- 用最近两次有效观测计算恒速预测，以实际时间间隔求预测位置；预测只用于关联，不导出预测坐标。
- 通过真实位移速度门限与预测误差门限构造可行配对，使用 SciPy `linear_sum_assignment`
  优先最大化有效配对数，再最小化预测距离；不是按检测数组次序或面积排名直接继承身份。
- 接近至少两条轨迹的预测位置、且面积明显大于它们各自历史面积的连通域标为 `merged_candidate`，
  相应轨迹输出 `occluded` 与 NaN，不把合并质心赋给某一条鱼。本方法不拆分合并轮廓。
- 未分配候选按面积顺序初始化新编号；`expected_fish_count` 限制同时活动轨迹数，
  experiment_001 为 5、后续视频为 4；不截断原始检测表，也不要求每帧检出相同数量。额外候选可为 `capacity_rejected`。
- 短缺失保留编号和 NaN；超过最大间隔后输出一次 `lost`，再次出现的新轨迹获得新编号。
  因此整段视频的编号总数可能超过配置数量，编号不等于已验证的真实鱼身份。

运动预测、全局分配、合并候选排除和数量上限属于工程扩展，论文未给出这些具体参数。
单纯位置预测仍可能在近距离交叉、转向、长期遮挡、反光和气泡干扰时发生错误关联。
`merged_candidate` 也是面积/距离启发式，不能作为人工确认的遮挡标签。

## 配置、缩放和坐标

已有 `video/preprocessing/rois/som/centroid` 配置继续生效。
新增 `multi_tracking` 参数均作用于恢复后的完整画面像素：

| 参数 | 单位和意义 |
| --- | --- |
| `expected_fish_count` | 已知群体数量，限制同时活动轨迹；experiment_001 为 5，后续视频为 4，synthetic 示例为 5 |
| `max_speed_px_s` | 最大观测位移速度，px/s |
| `max_gap_s` | 距上次有效观测的最大间隔，s，超过才终止编号 |
| `max_prediction_error_px` | 观测质心与恒速预测位置的最大距离，px |
| `merge_radius_px` | 大轮廓质心附近寻找多个预测位置的半径，px |
| `merge_area_ratio` | 大轮廓面积相对于历史单个轮廓的最小比例，必须大于 1 |

`multi_processing` 指定一个视角 `view`、分割尺度 `processing_scale`、
连续处理帧数上限 `max_frames` 和 ROI 来源说明 `roi_status`。
真实预览采用实体视角、0.25 尺度、前 60 帧；完整视频有报告的 19,380 帧，不能把本轮称为全片验收。
ROI 形状及所有算法门限是初步工程设置，不是实验人员测量或人工标签优化得到的值。

处理顺序：现有去畸变入口/中值滤波 → 裁剪原尺度 ROI → BGR 面积缩小 → HSV →
LBAdaptiveSOM → 全部候选质心 → 恢复原尺度 → 多目标关联。
缩小是当前逐像素 Python SOM 的预览运行措施，会改变分割及细小鱼体的可见性，不声称与原尺度等效。
没有标定文件时明确 `calibration_applied=false`。

缩放尺寸按 ROI 宽高乘配置比例取整，实际比例分别为 `sx=scaled_width/roi.width` 和 `sy`。
质心换算采用像素中心约定：

```text
full_x = roi.x + (scaled_x + 0.5) / sx - 0.5
full_y = roi.y + (scaled_y + 0.5) / sy - 0.5
area_px = round(scaled_area / (sx * sy))
```

输出坐标单位是 `px`、坐标系 `processed_full_frame`，不是模型三维像素或物理尺度。
输出面积仅为缩放轮廓的原尺度近似等效面积；`centroid.min_area_px/max_area_px` 和形态学核
针对**缩小后的掩膜**，不能与输出面积混用。manifest/逐帧表记录实际缩放比例。

## 运行与交付结果

```powershell
.\.venv\Scripts\python -m pip install -e '.[test]'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
.\.venv\Scripts\python -m fish3d multi-tracking-demo --config configs/synthetic_multi_tracking.yaml --output outputs/synthetic_multi_tracking_demo
.\.venv\Scripts\python -m fish3d track-multi-video --input data/raw/experiment_001.mp4 --config configs/experiment_001_multi_preview.yaml --output outputs/experiment_001_multi_preview
```

添加 `scipy>=1.11,<2` 依赖用于全局分配，不引入大型模型框架。
synthetic 示例只在实体视角生成五条分离的鱼形椭圆，先三帧空背景，一条鱼在两帧消失。
`synthetic_truth.csv` 是按配置独立生成的已知坐标，不是检测/跟踪输出，也不代表实验结果；
算法输出编号不会预设为真实标签编号。合成生成入口拒绝 experimental 配置。

| 输出 | 含义 |
| --- | --- |
| `frames.csv` | 所有处理帧的时间、来源、SOM 阶段、候选/有效/缺失/丢失计数、已知数量及缩放比例 |
| `detections.csv` | 所有通过面积门限的候选，含检测索引与分配/合并/容量拒绝状态，不因已知数量截断 |
| `tracks_2d.csv` | 已建立轨迹的原尺度质心和编号；短缺失/疑似遮挡/丢失输出 NaN |
| `scaled_masks/`、`cleaned_masks/` | 原始 SOM 与形态学后掩膜，尺寸为缩放后的 ROI，坐标原点为局部 (0,0) |
| `tracking_overlays/` | 原尺度画面中的实体 ROI、原尺度质心/段编号及候选数量，标题标注来源和身份未验证 |
| `tracks_2d.png` | 各编号的二维观测轨迹，NaN 处断线 |
| `som_model.npz` | 缩放 ROI 的 SOM 权重与来源/处理元信息 |
| `run_manifest.json` | 视频/配置哈希、配置快照、依赖版本、实际处理范围/计数、ROI 来源与验证状态 |

存在零候选的帧仍在 frames.csv 中；tracks_2d.csv 不在初始化前造出占位鱼。
所有实验输入和生成结果保存在 Git 忽略的 `data/` 和 `outputs/` 中。
旧 `reconstruct-tracks` 会拒绝同帧同视角多行，旧 `analyze-behavior` 也只接收每帧一条三维记录；
本轮多鱼二维表不得直接用于这些单鱼入口。

## 验证与尚未完成的事项

测试独立验证五个连通域、顺序打乱、非均匀时间及 XY 运动、交叉后的预测身份、
合并候选和全 NaN 遮挡、全局配对约束、短/长失踪、速度/预测门限、数量不补齐、
缩放转换、synthetic 来源保护和完整 SOM 示例链。真实视频只做短片段可运行性及输出检查，
没有人工检测/关联标签，不能报告召回率、识别准确率、ID 切换率或每条真实鱼成功率。

实际执行的基线为 100 项通过，增加多鱼测试后为 **122 项通过**。
合成视频处理 20 帧，得到 5 个连续段编号、83 个有效观测与 2 个明确缺失观测；
逐帧对应独立构造的五鱼坐标验证，前三帧空背景没有生成虚构的五条鱼。

以下为 experiment_001 的历史五鱼容量运行，与该原视频的最初数量一致；尚未验证真实检测或身份准确率。
真实视频仅检查 0.0–5.9 s 的 60 帧，得到了 758 个面积合格前景候选，
并非 758 条鱼；有效轨迹观测共 205 条，轨迹段累计 16 个、终止 11 个。
有效观测数量直方图为 0 条/1 帧、1 条/2 帧、2 条/9 帧、3 条/18 帧、4 条/19 帧、5 条/11 帧。
目视叠加图显示气泡和边缘前景产生额外候选，稳定身份未保持；
**真实多鱼稳定跟踪尚未通过验收**；原视频有五个观测也不能证明五条真实鱼均被正确检出。
下一步应先处理这些真实分割与关联问题，再评估跨视角对应。

完整多鱼系统仍需要：多视角多个候选的几何约束与歧义处理、跨视角身份一致性、
逐鱼三维轨迹与行为 CSV 接入，以及真实镜面/相机/水面参数和人工标签评价。
仅凭视角确认与总数量不能确定镜面角度、物理尺度或各帧一对一对应。

## 2026-10-15：新增视频与两项独立对照

### 数据与运行范围

新增 `VIDEO_20261014_EVE2.mp4`（2448×2048，报告约 10 fps，约 1790.647 s）和
`VIDEO_20261014_EVE3.mp4`（同尺寸，约 10 fps，约 1853.195 s）。
抽样阅读首段、中段、95% 位置的画面，仍有强气泡、暗鱼体和边缘前景。
以下历史试跑对三段视频均使用五鱼容量：experiment_001 数量正确，EVE2/EVE3 实为损耗一条后的四条，数量上限错误。
原视频三份 YAML 为 5，EVE2/EVE3 六份为 4；后者数量状态为 confirmed_by_user，左右映射仍按抽帧判断。
本节旧表保留历史诊断含义，EVE2/EVE3 不能当作四鱼条件下的验收结果。旧运行 manifest 保留五鱼配置快照与旧哈希，
当前 YAML 已变化，重放旧表应使用对应旧运行 manifest 的配置快照；回滚副本也只代表当时配置，不能当作真实数量证明。
每个视频只处理开头连续 60 帧，不能代表约半小时全片效果。

新视频实体 ROI 暂定 x=170,y=80,w=980,h=1440，镜像 ROI x=1360,y=350,w=900,h=1130，
均为抽帧估计；当前只处理实体。0.1 尺度得到 98×144 掩膜。
关联距离/速度按相对旧图像宽度的 2.55 倍初步缩放，未经真实标签优化。
三种变体在同一视频内部使用完全相同的 ROI、尺度、SOM 及其他参数。

### 可关闭的形状筛选

新增 `centroid.min_axis_ratio`，默认 1.0 表示关闭。每个面积合格组件按其前景像素
二阶中心矩计算 2×2 协方差矩阵，主次轴比为 `sqrt(lambda_max/lambda_min)`，与平移/方向无关。
圆/圆环约为 1，细长组件较大；单像素无方向，记为 1；退化直线记为 inf。
筛选不改变 SOM 掩膜，不修改质心或补写坐标，原论文基线始终保留。

人工构造五个不同方向的细长目标与十个圆气泡，原面积筛选得到 15 个候选，
轴比门限 2.0 保留五个目标、拒绝十个圆形组件。但真实目标会弯曲、迎面或被分割成碎块，
气泡也会变形/重叠，因此这不是经验证的鱼/气泡分类器。
真实试验门限 1.8 得到如下诊断结果：

| 视频 | 原候选 → 筛选后 | 原段数 → 筛选后 |
| --- | --- | --- |
| experiment_001 | 758 → 581 | 16 → 21 |
| EVE2 | 879 → 551 | 14 → 18 |
| EVE3 | 1241 → 704 | 13 → 16 |

候选减少但轨迹连续性变差，**不建议把形状门限作为当前默认优化**。
`*_multi_shape.yaml` 仅保留为可复现实验；不能据被拒绝数量统计真实气泡误检率。
`components.csv` 和新增逐帧诊断字段保留筛选前后证据。

### 连续观测确认

新增 `multi_tracking.birth_confirmation_frames`，正整数、默认 1（旧行为）。
配置为 3 时，新候选进入内部暂存、在检测表标为 tentative；连续三个帧号的观测
完成关联后才分配正式段号，只写当前实测点，前两帧不回填。
未确认候选错失即移除，跳帧重置确认计数；没有虚构 lost 段或物理鱼编号。
暂存候选不占已确认轨迹容量；正式活动轨迹不超过所配置数量，原视频为五条、后续视频为四条。
分配先保留门限内可行的已确认轨迹，再分配其他候选；身份仍未由外观或人工标签证明。
正式轨迹短失踪保留编号、NaN 和原最大缺失时长，长失踪仍重新编号。

不启用形状限制，仅把确认帧数从 1 改为 3 的真实对照：

| 视频 | 正式段数 1帧 → 3帧 | 有效观测数 1帧 → 3帧 |
| --- | --- | --- |
| experiment_001 | 16 → 15 | 205 → 181 |
| EVE2 | 14 → 12 | 194 → 174 |
| EVE3 | 13 → 8 | 201 → 193 |

正式编号的碎片数量减少，但确认会延迟轨迹输出并丢弃短暂出现的真实目标。
减少段数不等于身份更准；气泡仍可能持续超过三帧并被正式跟踪，当前仍不能通过稳定多鱼验收。
默认 1 的新实现重放三个旧基线的检测 CSV，290/285/290 条观测逐项完全一致。

### 使用与可追溯对照

`configs/eve2_multi_preview.yaml`、`eve3_multi_preview.yaml` 为面积基线；
`*_multi_shape.yaml` 仅改变轴比门限；`*_multi_confirmed.yaml` 仅改变确认帧数。
experiment_001 使用原有 preview 配置以及新增 shape/confirmed 配置。

```powershell
.\.venv\Scripts\python -m fish3d track-multi-video --input data/raw/VIDEO_20261014_EVE2.mp4 --config configs/eve2_multi_preview.yaml --output outputs/optimization_20261015/eve2_baseline
.\.venv\Scripts\python -m fish3d track-multi-video --input data/raw/VIDEO_20261014_EVE2.mp4 --config configs/eve2_multi_confirmed.yaml --output outputs/optimization_20261015/eve2_confirmed
.\.venv\Scripts\python scripts/compare_multi_runs.py --parameter confirmation --baseline outputs/optimization_20261015/eve2_baseline --filtered outputs/optimization_20261015/eve2_confirmed --output outputs/optimization_20261015/eve2_confirmation_comparison.json
```

形状对照使用 `--parameter shape` 和对应 shape 目录。比较脚本要求同一输入哈希、视角、
处理时间范围和尺度，且配置仅允许指定参数变化；逐帧 SOM 掩膜还须逐字节相同。
本轮三视频、三变体共九次运行，每组对照的前景掩膜完全相同，避免用更换分割结果冒充关联改善。
所有实验输出仍为 experimental，构造测试为 synthetic；真实准确率与物理身份验证标记为 false。
人工反馈和视频条件要求见 `video_feedback.md`；真实鱼身份/召回仍须人工参考标签。
