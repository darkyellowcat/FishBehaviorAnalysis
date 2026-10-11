# S4：单鱼质心提取与二维时间跟踪

## 范围与算法来源

本项目沿用用户确认的八阶段顺序：S4 做质心与时间跟踪，S5 做双视角对应
与三维重建。任务书的阶段表把后两项并入 S4，编号有差异；本轮不据此扩展范围。

原论文《基于3D计算机视觉的鱼类行为分析研究》第 252 页第 2.2 节描述从
前景二值图计算左右两视角质心。规划书第 8.1 节和开发任务书第 4.5 节
明确前景像素均值公式，以及先用一条鱼测试的要求：

```text
x_local = sum(foreground_pixel_x) / N
y_local = sum(foreground_pixel_y) / N
x_full = x_local + roi_x
y_full = y_local + roi_y
```

面积 N 为选中连通域的像素数量，含空洞的区域不会把空洞计入面积或质心。
N=0 返回缺失；合法的图像原点 (0,0) 仍是有效位置。
论文未给出完整的时序关联、连通域筛选与形态学参数，下述规则均为工程设计。

## 模块与输入输出

- `ConnectedComponentCentroidExtractor.extract(ForegroundMask)` 兼容既有
  `CentroidExtractor` 接口，输出一个有效 `Detection2D` 或 None。
- 输入必须为非空二维 uint8 的 0/255 掩膜；先开运算，再闭运算，均使用方形
  核、一次迭代和零值边界；核尺寸为 0 时禁用对应操作。原始掩膜不被修改。
- 按配置的 4/8 邻域计算连通域，保留面积在 `[min_area_px,max_area_px]`
  内的候选，取面积最大者；同面积按质心 y、x 升序确定。
  `last_candidate_count` 用于暴露多个候选；`last_cleaned_mask` 为形态学后的
  全部前景，不代表只剩选中连通域。
- `SingleFishTracker.update(Detection2D)` 每帧处理一次，`track(sequence)`
  与既有 `DetectionTracker` 序列接口兼容。缺失帧由 `missing_detection`
  构造：两个坐标为 NaN、面积 0、is_valid=false。
- `TrackedDetection` 保持原合同。帧号及时间严格递增，输入必须属于实例的
  固定视角；非法输入报错，不用于更新跟踪状态。

两个 ROI 分别维护一个跟踪器。坐标原点为经过 S2 处理的完整图像左上角，
x 向右、y 向下，单位 px；启用去畸变时属于去畸变后的图像，不是原始畸变
图像坐标，更不是世界坐标。

## 时间关联规则

设最近接受的检测为 P_last，时间为 t_last。当前有效检测 P 的关联条件为：

```text
dt = timestamp_s - t_last
dt <= max_gap_s
norm(P - P_last) <= max_speed_px_s * dt
```

距离包含 x 和 y，直接使用秒时间戳，不从帧号推断采样间隔。
位移门限超出时保留原始检测表中的有效位置，但跟踪表输出 NaN、面积 0、
is_valid=false，状态为 rejected；不会把跳变点作为后续关联参考。
这些门限是图像关联规则，不是游动速度或异常行为阈值。

短时缺失保留轨迹段编号，输出 missing；未检测到首点时编号为空，状态为
uninitialized。距最后接受点超过 max_gap_s 时清除旧参考，再出现有效检测
会建立新的编号，状态为 initialized。连续接受时为 tracked。

编号采用 `real_0001`、`mirror_0001` 等视角内轨迹段标识。长失踪后编号递增；
编号不能证明物理鱼身份，也没有建立 real 与 mirror 的对应关系。
不插值、不输出预测位置；图表与逐帧连线在缺失或编号变化处中断。

## 配置与运行

`configs/synthetic_tracking.yaml` 包含已有 S2/S3 设置和新增字段：

| 参数 | 示例值 | 口径 |
|---|---:|---|
| centroid.min_area_px / max_area_px | 40 / 500 | 形态学后连通域像素数，工程示例 |
| centroid.opening_kernel / closing_kernel | 3 / 3 | 0 禁用，或至少为 3 的奇数 |
| centroid.connectivity | 8 | 4 或 8 |
| tracking.max_speed_px_s | 80 | 实际时间间隔中的最大图像位移速率 |
| tracking.max_gap_s | 0.5 | 距最后接受点的最大持续时间 |
| synthetic_video.missing_frame_ids | [8,9] | 两视角均不绘制鱼的帧，仅用于 synthetic 测试 |

以上新增门限不是论文实验参数，不适用于所有真实视频。
合成生成器的 missing_frame_ids 默认空序列，保留原 S2/S3 行为。
本例前 3 帧为空背景，之后按已知正弦位置绘制两个椭圆；第 8、9 帧消失。
程序仍从解码图像经 SOM 掩膜计算质心，没有读取预设位置作为检测输出。

```powershell
.\.venv\Scripts\python -m fish3d tracking-demo --config configs/synthetic_tracking.yaml --output outputs/synthetic_tracking_demo
.\.venv\Scripts\python -m fish3d track-video --input outputs/synthetic_tracking_demo/synthetic_input.avi --config configs/synthetic_tracking.yaml --output outputs/synthetic_tracking_replay
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

## 结果文件与验收

S3 分割直接复用，在 `foreground/` 保存全部分割产物与其运行记录。
S4 从这些掩膜及分割 CSV 的帧号、时间和 ROI 原点提取检测，不再次解码视频。

- `detections.csv`：每帧每视角一行，包含原始质心、面积、有效性、候选数。
- `tracks_2d.csv`：同样每帧两行，附带 fish_id 与 status；原始跳变检测可能有效，
  对应跟踪结果被门限拒绝。无效坐标写为 nan。
- 两表共同保存 timestamp_source、ROI 原点、coordinate_unit=px、
  coordinate_frame=processed_full_frame 和 data_source。
- `cleaned_masks/<view>/`：形态学后掩膜，二值 PNG。
- `tracking_overlays/`：S3 叠加图上画质心与相邻有效点；绿色为 real、青色为
  mirror，黄色叉为被拒绝的检测。合成示例保留 SYNTHETIC 字样。
- `tracks_2d.png`：两个视角各自的二维图像轨迹；标题带数据来源。
- `run_manifest.json`：配置快照、输入/配置/S3 记录 SHA-256、算法版本、
  依赖版本、逐视角有效/拒绝计数、耗时与限制。

单元测试覆盖精确像素均值、空洞、ROI 偏移、空前景与原点、面积筛选及并列、
形态学、连通性、静止与非均匀时间、二维跳变、短失踪、长失踪及输入合同。
synthetic 集成测试核验缺失帧、编号保持、输出表及相对已知椭圆中心的误差；
该误差仅验证合成测试数据，不是实际鱼类检测准确率。

## 已知限制与真实视频适配需求

当前单鱼方法可能选中更大的反光连通域；多鱼或合并前景不满足模型假设。
只做最大区域筛选和时间门限，未实现多候选时序优化、遮挡预测或物理身份恢复。
形态学会改变面积与质心，零值边界可能削弱贴近 ROI 边缘的鱼体。
SOM 首帧纳入鱼体及色相线性更新等限制仍见 `lbadaptive_som.md`。
当前没有真实视频验证或实时性能承诺。

实验人员需提供：确认单鱼数量的双视角短视频、真实 ROI/标定及时间记录、
正常鱼体像素面积范围、代表性的反光/遮挡/出视野片段，以及少量人工质心或
目标掩膜和缺失帧标注。算法侧据此评估质心误差、有效检测率与轨迹中断情况，
调整参数；实验数据采集由实验人员负责。
