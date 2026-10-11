# S6 规则行为识别与可视化

## 完成范围与依据

遵循用户阶段划分，本阶段实现行为规则、轨迹 CSV 接入、运动计算复用、图表和可追溯导出。
S0–S5 接口和算法保持原有行为；不包含 S7 的真实视频调参、人工标签评价或最终实验验证。

依据 `baseDocs/基于3D计算机视觉的鱼类行为分析研究.pdf` 第 253 页 §2.4 和表 1：

| 规则编号 | 论文条件 | 本项目实现 |
| --- | --- | --- |
| `frantic_swimming`（狂游） | v > v0 或 r > r0 | 速度大小或角速度超过配置阈值 |
| `float_surface`（长时间漂浮水面） | z = h 且持续 t > 15 s | `abs(Z-h) <= surface_tolerance`，连续观测持续时间严格大于配置值 |
| `jump_out`（跳出水面） | z > h | 有效坐标 Z 严格大于配置水面高度 |

论文 h=182、v0=45、r0=1.7 是既往实验参考，不是本装置测定值。
论文表中 r 阈值没有充分交代可迁移的单位/采样口径；本工程明确使用 **rad/s**。
S1 按任务书采用转向角除以外侧两点时间差，具体口径见 `motion_method.md`；
论文式 (6)/(7) 中 2Δt 与文字时间跨度的定义存在歧义，本轮保留 S1 口径，没有未经说明改动数学模块。
数值 1.7 只能作为参考，不能声称与原实验角速度阈值经过量纲和采样方式校验。

水面容差、最大连续间隔、最小方向位移以及事件边界约定属于本项目工程处理，
并非论文额外提供的参数。没有加入漂浮时低速、跳跃时上升速度或狂游最短持续时间条件。
水面附近移动也可能满足论文“漂浮”规则，不能据此证明鱼真正静止或生物学异常。

## 输入、接口和单位

`analyze-behavior` 输入 S1/S5 的三维 CSV，包含完整 `TrajectoryPoint` 字段。
目前沿用 S5 单鱼输入合同：每帧一条坐标记录，帧号和时间戳全局严格递增，
可以包含多个轨迹段编号和 `unassigned` 无效记录；不接收同帧多鱼。
无效点必须同时具有 `is_valid=false` 和三个 NaN 坐标。

`RuleBehaviorRecognizer.detect(trajectory, speed, angular_speed)` 兼容已有 `BehaviorRecognizer`。
直接调用只接受一条鱼的有序轨迹，两个特征数组与该轨迹一一对齐。
`evaluate` 另外返回逐帧规则标记。CSV 入口按 fish_id 分组调用规则接口。

配置的来源、单位、坐标系必须逐条匹配输入。Z 必须是向上增加的高度轴，
水面高度须位于同一坐标系；代码无法仅凭字符串证明坐标轴方向正确。
高度、容差、最小位移使用 `coordinate_unit`，速度阈值使用该单位/s，
角速度阈值使用 rad/s，持续时间和连续间隔使用 s。
S5 的 `model_px/paper_ideal_cartesian` 输出仍是未经真实验证的理想模型，不能理解成毫米或实际水面高度。

## 参数与时间约定

配置文件的 `behavior` 映射必须提供下列字段，没有隐藏的实验常量：

| 参数 | 意义 |
| --- | --- |
| `data_source` | synthetic 或 experimental，必须与输入一致 |
| `coordinate_unit` / `coordinate_frame` | 阈值所对应的单位与坐标系 |
| `water_surface_z` | 经相同坐标变换表达的水面高度 |
| `surface_tolerance` | 水面判定的双侧高度容差；0 对应精确相等 |
| `floating_duration_s` | 严格超过后才触发漂浮；示例 15 s 取自论文 |
| `frantic_speed` | 三维速度大小的严格上限阈值 |
| `frantic_angular_speed_rad_s` | 转向角速度的严格上限阈值 |
| `max_gap_s` | 相邻有效观测允许的最大时间间隔（包含等号） |
| `min_direction_displacement` | S1 判断方向向量是否有定义的最小位移 |

只有同编号、连续帧号、两点有效且时间间隔不超过 `max_gap_s` 才形成连续段。
先分段，再调用 S1：中心速度 `(P_next-P_prev)/(t_next-t_prev)` 使用 XYZ，
角速度为两段三维位移夹角除以 `t_next-t_prev`；段首尾速度/角速度为 NaN。
缺失点不插值，不跨间隔求差分；累计长度按 fish_id 累加实际观测到的相邻三维步长，
保留此前长度，但不补失踪距离。零长度/很短向量使转向角未知，不伪造角速度为 0。

水面持续时间为当前观测时间减去本次连续水面段第一点的时间。
缺失、离开容差、漏帧、超时或编号变化都会重置。狂游的一个有限特征超阈值即可触发；
未触发时只有两个特征都有限才可明确判定该规则为假，否则为未知。
规则互相独立：例如略高于水面、仍在容差范围内的点可同时满足跳出和持续漂浮，
不强行加优先级或排他条件。

事件只连接连续且规则成立的观测点。漂浮事件从**首次超过持续时间阈值的采样时刻**开始，
不回填最初水面接触时刻；可用逐帧 `timestamp_s-surface_duration_s` 找到水面接触起点。
事件结束是最后一条规则成立的观测，单点事件起止相等、观测跨度为 0；
不推断下一帧或缺失期间的真实起止时间。

## 运行与结果

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
.\.venv\Scripts\python -m fish3d behavior-demo --config configs/synthetic_behavior.yaml --output outputs/synthetic_behavior_demo
.\.venv\Scripts\python -m fish3d analyze-behavior --input outputs/synthetic_geometry_demo/trajectory_3d.csv --config configs/synthetic_behavior_model.yaml --output outputs/synthetic_behavior_video_replay
```

第一个示例按 YAML 的采样间隔、分段起点和速度构造 51 条坐标观测，包含水下缓游、
加速、水面静止和高于水面的位置段。坐标转折是软件测试构造，不是鱼类动力学或真实跳跃模型。
示例不预写行为结果；运动和规则模块从坐标计算预测。
全部轨迹、CSV、运行记录和图标题标为 synthetic，生成器拒绝 experimental 配置。
第二个示例复用已验收 S5 合成视频重建 CSV 的 18 帧，检查不同模型单位和缺失帧接入。
两份配置的单位与水面值不同，不能相互套用；后者的 32 model_px 也只是测试设置。

| 文件 | 内容 |
| --- | --- |
| `trajectory_3d.csv` | 仅 behavior-demo 生成的 synthetic 输入；分析现有 CSV 时不重写输入 |
| `motion.csv` | 复用 S1 输出，逐帧三维步长、累计观测长度、速度、方向、转角、角速度及来源/单位 |
| `behavior_samples.csv` | 三个规则的逐帧布尔标记、水面持续时间、is_valid、frantic_evaluable、编号及来源/单位 |
| `behavior_events.csv` | 编号、规则、起止秒数、观测跨度、来源/坐标系/单位及 `result_type=rule_prediction` |
| `trajectory_3d.png` | 各连续段分别绘制的三维轨迹，不跨缺失或编号变化连线 |
| `motion_behavior.png` | 随时间变化的速度、角速度和高度，以及各阈值线/水面容差带 |
| `behavior_timeline.png` | 规则成立的观测标记；另行标出无效坐标及狂游规则未知的观测 |
| `run_manifest.json` | S6/规则版本、依赖版本、输入和配置 SHA-256、完整配置、来源、单位、计数和已知限制 |

所有 CSV 保留无效观测，NaN 不转换为零。无效/未知帧的 false 表示没有检出，
不得将其统计为已确认正常；跳出/漂浮以 `is_valid` 判断是否可评价，
狂游另外需要 `frantic_evaluable`。没有事件时事件 CSV 仍保存表头。
结果与本地回滚资料统一位于 Git 忽略的 `outputs/`，不上传生成视频或实验数据。

## 实际验证与后续实验数据需求

新增测试覆盖严格阈值、零向量、三维速度/转角、非均匀采样、水面容差、
持续时间重置、时间大间隔、缺失帧、编号分段、单位/来源合同、全缺失、
CSV/图表/哈希和 synthetic 来源保护。实际执行结果记录在 `progress.md`。

尚未实施真实行为准确率评价、噪声滤波或阈值优化。后续由实验人员提供：

- 原始视频及可靠时间信息，确认鱼在两个视角的可见性及遮挡区间。
- 同坐标系的水面标定、Z 轴方向、镜面/相机/鱼缸参数和尺度误差；模型单位与物理尺度的验证记录。
- 正常及各异常行为的人工起止标签、判定标准，尤其“漂浮”是否需额外低速条件、“跳出”如何判定。
- 多种正常状态下的速度/角速度分布，采样率与噪声水平，用于确定阈值、容差、最大连续间隔和最小方向位移。

算法侧读取、校验和评价这些资料；物理实验与采集由实验人员负责。
在取得数据并由用户确认前，不进入 S7，不报告真实识别准确率。
