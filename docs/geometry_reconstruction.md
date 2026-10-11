# S5：双视角对应与论文理想模型三维坐标

## 范围与依据

本轮沿用用户确认的阶段顺序，只实现 S5 双视角对应及理想模型重建。
原论文《基于3D计算机视觉的鱼类行为分析研究》第 250 页图 2、第 251 页
式 (1) 给出镜面几何关系；第 252 页以实体和镜像鱼质心作为匹配点。
规划书第 8 节/第 14–15 页把它解释为图像像素形式：

```text
X = x_real
Y = y_real
Z = (a - x_mirror) * tan(alpha)
```

原论文的 a 是几何距离，规划书又把 285 用作图像分界值，两者并非在任意
装置中自动等价。当前实现是规划书意义下的理想像素模型，保留原式，不把
图像数值解释为鱼缸物理尺寸；透视、镜面姿态和折射还需实际参数及验证。

## 坐标与单位约定

| 数据 | 坐标系与单位 |
|---|---|
| S4 输入 | processed_full_frame、px；完整处理图像，x 向右，y 向下 |
| S5 输出 | paper_ideal_cartesian、model_px；论文式的模型代理坐标 |
| 鱼缸世界坐标 | 本阶段未建立；原点、轴向、尺度须由实验与标定确认 |

设配置的图像原点为 (origin_x,origin_y)，镜面几何参考线的完整图像横坐标
为 a_px，代码实际计算：

```text
X = x_real - origin_x
Y = y_real - origin_y
Z = (a_px - x_mirror) * tan(mirror_angle_deg * pi / 180)
```

Z=0 对应 x_mirror=a_px；镜像点在参考线左侧时 Z 为正。
这只是模型的正负方向，不证明实验中的鱼缸底面及世界轴向已确定。
如果用移动后的图像原点解释论文的 a，则 a_model=a_px-origin_x，
x_mirror_model=x_mirror-origin_x，两者差值保持不变。

`mirror_intersection_x_px` 独立于 real/mirror ROI 的边界。示例中它恰好等于
64，是 synthetic 参数选择；程序不会从 ROI 宽度推导或覆盖几何参考值。
单位与坐标系配置必须是 model_px 和 paper_ideal_cartesian，尝试配置 mm
或 tank_world 会报错。负 Z 不被偷偷截成 0；is_valid 只表示检测、对应和
数值计算有效，不等于物理位置合理或几何已验证。

## 双视角匹配

`SingleFishDualViewMatcher.match(real,mirror)` 实现既有匹配接口。输入顺序
必须正确，两个检测须具有相同 frame_id 和完全相同的 timestamp_s；缺失、
跟踪被拒绝或轨迹编号为空时不匹配。

当前假设每视角只有一条鱼，并按理想坐标对齐关系检查：

```text
abs(y_real - y_mirror) <= matching.max_y_disparity_px
```

该门限是工程检查，不是论文规定的参数，不是经过标定的极线约束。
真实透视或镜面安装可能使纵坐标不同，需要实验参考点建立对齐关系，不能仅
靠放宽门限声称匹配正确。real_0001 与 mirror_0001 是各自视角编号，
不要求字符串相等，也不通过编号证明物理身份。

结果状态包括 matched、frame_mismatch、timestamp_mismatch、
invalid_detection、missing_track_id、y_disparity_exceeded；CSV 中整行
缺失一视角时记为 missing_view。没有为缺失视角伪造有效检测。

## 重建接口与标定入口

- `PaperIdealReconstructor.reconstruct(real,mirror)` 实现既有重建接口，输出
  `TrajectoryPoint`。直接调用时不允许异帧、异时间或错误视角；任一视角
  无效则返回全 NaN 三维坐标。调用者需先通过匹配检查。
- `project(point)` 为理想式的代数逆映射，供已知三维 synthetic 点测试：
  real=(X+origin_x,Y+origin_y)，mirror=(a_px-Z/tan(alpha),real_y)。
  它不是相机光线、真实平面镜反射或含水介质的渲染模型。
- 三维编号由两条视角内轨迹段编号组成，例如 real_0001__mirror_0001。
  任一视角重新编号后产生新配对段；首个成功对应前用 unassigned 保存无效帧。
  暂时匹配失败的点沿用最近配对段编号，但坐标仍全部无效。
- 三维图在缺失和编号变化处断开。轨迹 CSV 可包含多个配对段；后续使用 S1
  单鱼运动接口时应按 fish_id 分组，排除 unassigned，保留各段缺失标记。

S2 的 `preprocessing.calibration_file` 继续作为相机内参与畸变 JSON 入口。
S5 可以读取并校验该文件尺寸，记录文件及 SHA-256；相机内参本身不能赋予
该简式物理尺度。输入 CSV 只能声明 processed_full_frame，不能单独证明
上游已实际去畸变，因此运行记录明确保留该验证缺口。

没有提供未经验证的毫米换算、虚构的镜面标定或校准光线模型。
镜面角度参数可取 (0,90) 内的值；非 45° 测试只验证式 (1) 的数值计算，
不验证对应装置的投影/反射关系。

## 配置、运行与产物

`configs/synthetic_geometry.yaml` 复用 S2–S4 的示例设置，并新增：

| 参数 | 示例值 | 来源/含义 |
|---|---:|---|
| matching.max_y_disparity_px | 3 | 理想对齐视图的工程示例门限 |
| geometry.mirror_angle_deg | 45 | 原论文基准角度，尚非本实验测量值 |
| geometry.mirror_intersection_x_px | 64 | synthetic 的完整图像几何参考 |
| geometry.image_origin_px | [0,0] | 图像到模型 X/Y 的坐标平移 |
| geometry.coordinate_unit | model_px | 强制标明模型单位 |
| geometry.coordinate_frame | paper_ideal_cartesian | 代理模型坐标系 |

```powershell
.\.venv\Scripts\python -m fish3d geometry-demo --config configs/synthetic_geometry.yaml --output outputs/synthetic_geometry_demo
.\.venv\Scripts\python -m fish3d reconstruct-tracks --input outputs/synthetic_tracking_demo/tracks_2d.csv --config configs/synthetic_geometry.yaml --output outputs/synthetic_geometry_replay
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

geometry-demo 实际生成 synthetic 视频，运行 S2–S4 后，从 S4 掩膜计算出的
跟踪表进行三维计算，不把预设椭圆坐标充当检测结果。reconstruct-tracks
可直接使用既有 S4 CSV，不重复分割。输入表须明确 px、processed_full_frame
和统一 data_source；ROI 原点须与配置相同，有效点须落在其完整图像 ROI 内，
以检测局部坐标误用。每帧每视角至多一行，帧和参考时间按序。

- `matches.csv`：逐帧两视角编号、存在性、时间及来源、纵向偏差、匹配状态。
- `trajectory_3d.csv`：既有三维合同，每个输入帧一行；匹配失败时 X/Y/Z 均为
  NaN，而不是仅留下有效实体鱼的 X/Y 或推测 Z。
- `trajectory_3d.png`：带来源和未验证理想模型说明的三维图。
- `run_manifest.json`：输入 CSV 与配置哈希、配置快照、算法/依赖版本、
  状态计数、模型单位、相机文件记录及 metric_calibration_applied=false、
  geometry_validated_on_real_data=false。
- 完整视频示例另在 `tracking/` 保留 S4 产物及其 S3 分割、运行记录。

## 验证与真实实验需求

测试包括论文的 45° 数值例、30° 的独立数学参考、已知 XYZ 各自变化的逆向
一致性、非均匀时间、非零原点、独立几何参考、缺失坐标、严格同步、纵向门限、
编号不相等及变化、单位/来源/ROI 检查、重复行、全缺失和相机 JSON 尺寸校验。
合成视频的误差只相对于预设椭圆和理想式，不构成真实鱼缸三维误差指标。

后续由实验人员交付：

1. 单鱼双视角原视频、逐帧时间或可靠帧率，实际 ROI 和固定装置参考画面。
2. 相机内参与畸变、标定尺寸和重投影误差，以及相机相对鱼缸的姿态/位置信息。
3. 镜面实际平面位置、法向/倾角、鱼缸底面和世界坐标原点/轴向的约定。
4. 分布于不同空间位置与高度的已知参考点、物理单位及双视角对应像素，
   用于检验理想式、估计尺度并报告独立验证误差。
5. 水位、玻璃与水界面位置/厚度及必要的折射信息，供判断简化模型偏差。

算法侧负责读取、数学模型实现和误差分析；物理布置、标定数据采集及实验
由实验人员完成。目前未获得这些资料，不声称已恢复真实物理三维轨迹。
