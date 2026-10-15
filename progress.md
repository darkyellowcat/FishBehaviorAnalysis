## 2026-10-09 - Task: S0 工程框架与数据接口

### What was done

- 建立 Python 3.11 包、依赖与配置、验证脚本、轨迹数据合同和后续视频算法接口。
- 规定时间戳、坐标单位、坐标系、无效坐标和 synthetic 来源的校验规则。

### Testing

- 执行 `py -3.11 -m venv .venv` 和 `.\.venv\Scripts\python -m pip install -e '.[test]'`，均成功。
- 执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：4 passed in 0.05s。

### Notes

- `.gitignore`：忽略虚拟环境、缓存和生成输出。
- `pyproject.toml`：声明包、Python 版本、S0/S1 依赖和测试入口。
- `configs/default.yaml`：给出明确标为 synthetic 的示例参数。
- `src/fish3d/__init__.py`：声明包版本。
- `src/fish3d/schemas.py`：定义轨迹点及序列校验。
- `src/fish3d/config.py`：定义配置读取及参数校验。
- `src/fish3d/interfaces.py`：定义后续视频、分割、质心、重建和行为模块合同。
- `scripts/verify.ps1`：提供固定 pytest 验证入口。
- `tests/test_contracts.py`：验证配置与关键数据规则。
- `docs/data_contract.md`：记录字段、坐标和实验数据交接约定。
- `README.md`：说明项目用途、安装、运行命令及阶段。
- `progress.md`：追加本轮实施与验证记录。
- 回滚点：本仓库目前没有 Git 提交；只需删除上列本轮新增文件（含本轮 `progress.md`），并删除本轮创建的 `.venv`，保留原有四份参考资料。删除前按上述清单逐项核对。

## 2026-10-09 - Task: S1 合成三维轨迹与运动特征

### What was done

- 实现可重复的 synthetic 螺旋轨迹、三维逐步位移、累计路径、中心差分速度、方向、转向角和角速度。
- 导出轨迹与运动 CSV、三张 PNG 图和包含配置快照及哈希的运行记录；修正近常量曲线的纵轴显示。
- 补齐后续接口的 ROI 原点、鱼 ID 跟踪和双视角匹配合同，并记录角速度口径与未验证限制。

### Testing

- 执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：15 passed in 0.13s。
- 执行 `.\.venv\Scripts\python -m fish3d simulate --config configs/default.yaml --output outputs/synthetic_demo`：成功。
- 检查两份 CSV 各 121 行，来源均为 synthetic、单位均为 synthetic_unit；配置 SHA-256 与源文件一致，运行记录所列文件均存在。
- 检查三张 PNG 格式与尺寸，并目视确认轨迹和两条曲线显示正常。

### Notes

- `configs/default.yaml`：增加方向与转向的最小位移阈值。
- `src/fish3d/config.py`：校验新增阈值。
- `src/fish3d/interfaces.py`：补充 ROI 原点、跟踪和双视角匹配接口。
- `src/fish3d/synthetic.py`：生成确定性的 synthetic 三维轨迹。
- `src/fish3d/motion.py`：计算三维位移、路径、速度、方向和角速度。
- `src/fish3d/export.py`：写入轨迹、运动及运行来源文件。
- `src/fish3d/visualization.py`：输出三维轨迹与运动曲线。
- `src/fish3d/__main__.py`：提供合成示例命令行入口。
- `tests/test_motion.py`：覆盖静止、直线、转弯、非均匀时间、缺失、零向量、跳帧和单位。
- `docs/data_contract.md`：说明补齐后的后续模块接口。
- `docs/motion_method.md`：记录 S1 公式、角速度口径和已知限制。
- `progress.md`：仅在末尾追加本轮记录。
- 回滚点：仓库仍无 Git 提交；如需退回本轮前的空工程状态，先执行 `git clean -nfd -- .gitignore README.md pyproject.toml progress.md configs src tests scripts docs` 核对清单，再执行同一命令去掉 `-n`。该命令不触及四份原始参考资料；`outputs/` 与 `.venv/` 可按需单独删除。

## 2026-10-09 - Task: S2 视频读取、预处理与双视角分区

### What was done

- 新增 OpenCV 视频逐帧读取、时间戳来源记录、可选相机去畸变、中值滤波、HSV 转换和配置化双视角 ROI 裁剪。
- 生成带 SYNTHETIC 字样的合成 AVI，保存逐帧 PNG、HSV `.npy`、`frames.csv` 与来源/配置哈希记录。
- 记录真实视频接入所需的标定、ROI 和时间戳资料；保留 S0/S1 轨迹分析命令。

### Testing

- 开工前执行固定验证脚本：15 passed in 0.11s。
- 首轮 S2 测试为 18 passed、1 failed：Windows 中文临时路径下 `cv2.imwrite` 返回失败；改为 OpenCV 内存编码及 Python 文件写入后修复。
- 最终执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：21 passed in 0.28s。
- 执行 `video-demo`：成功处理 12 帧 synthetic AVI；核验 7 类输出各 12 份、HSV/ROI 数组形状及裁剪位置、时间戳递增、视频/配置 SHA-256、来源标记和标定状态；目视检查处理图像。
- 再次执行 S1 `simulate` 与独立 `preprocess-video` 命令：均成功，后者处理 12 帧。

### Notes

- `pyproject.toml`：加入 OpenCV 无界面运行依赖。
- `configs/synthetic_video.yaml`：配置合成视频、滤波、标定入口与双视角 ROI。
- `src/fish3d/interfaces.py`：扩展视频帧来源与完整预处理结果接口。
- `src/fish3d/video_config.py`：读取并校验 S2 配置及 ROI。
- `src/fish3d/video_io.py`：读取视频及生成标记 synthetic 的示例 AVI。
- `src/fish3d/preprocessing.py`：实施去畸变接口、中值滤波、HSV 与 ROI 裁剪。
- `src/fish3d/video_processing.py`：保存逐帧结果、时间表和运行记录。
- `src/fish3d/__main__.py`：增加 S2 演示与已有视频处理命令。
- `tests/test_video_s2.py`：验证 ROI、滤波、HSV、非零畸变、时间戳回退及落盘结果。
- `README.md`：说明 S2 安装、命令、输出和阶段状态。
- `docs/data_contract.md`：更新视频与后续算法的接口状态。
- `docs/video_preprocessing.md`：记录处理顺序、数据格式、局限及真实视频需求。
- `progress.md`：只在末尾追加本轮记录。
- 回滚点：仓库仍没有 Git 提交。若要撤销到项目创建前，先执行 `git clean -nfd -- .gitignore README.md pyproject.toml progress.md configs src tests scripts docs` 核查目标，再去掉 `-n` 执行；该命令不包含四份原始资料。若只撤销 S2，应先备份 S0/S1 工程，再按本轮文件清单逆向恢复，不要无差别清理仓库。
- 勘误：完成范围检查时确认 S0/S1 已有基线提交 `9c8bde4`，上条“没有 Git 提交”不适用于当前仓库。仅回滚 S2 时，执行 `git restore -- README.md docs/data_contract.md progress.md pyproject.toml src/fish3d/__main__.py src/fish3d/interfaces.py`，并先用 `git clean -nfd -- configs/synthetic_video.yaml docs/video_preprocessing.md src/fish3d/preprocessing.py src/fish3d/video_config.py src/fish3d/video_io.py src/fish3d/video_processing.py tests/test_video_s2.py` 预览新增文件，再去掉 `-n` 执行；这些命令不触及 S0/S1 已提交文件的基线版本。

## 2026-10-09 - Task: 管理 Git 忽略规则与本机 IDE 文件

### What was done

- 扩展忽略规则，排除本机环境、缓存、构建及测试产物、编辑器状态、环境密钥文件、实验数据与生成结果。
- 将已经跟踪的 10 个 IDE 文件移出 Git 索引，保留本地文件；源码、配置、测试和项目参考资料继续纳入版本管理。

### Testing

- 用 `git check-ignore --no-index --stdin -z` 验证 18 个应忽略路径和 13 个应保留路径，全部符合预期。
- 检查 Git 索引已无 `.idea/` 文件，本地 10 个文件均存在；`workspace.xml` SHA-256 与改动前一致。
- 本轮仅修改仓库文件管理规则，采用 Git 规则和索引检查验证，无算法改动。

### Notes

- `.gitignore`：补全 Python 工程、本机文件及数据忽略规则。
- `docs/repository_files.md`：说明提交边界、规则检查方式及索引移除与历史提交的区别。
- `progress.md`：在末尾追加本轮验证记录。
- `.idea/copilot.data.migration.agent.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/copilot.data.migration.ask.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/copilot.data.migration.ask2agent.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/copilot.data.migration.edit.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/fish.iml`：仅从 Git 索引移除，保留本地文件。
- `.idea/inspectionProfiles/profiles_settings.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/misc.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/modules.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/vcs.xml`：仅从 Git 索引移除，保留本地文件。
- `.idea/workspace.xml`：仅从 Git 索引移除，保留用户的本地修改。
- 回滚：执行 `git restore --source=9c8bde4 --staged -- .idea` 恢复索引，执行 `git restore -- .gitignore` 恢复旧规则；删除新增的 `docs/repository_files.md`，并只删除本日志最后的本轮条目，保留前面的 S2 未提交记录。本轮未执行提交或推送，也未清除远端历史。



- 索引复核：执行 git ls-files -ci --exclude-standard，结果为空；当前索引没有已跟踪但又命中忽略规则的文件。

## 2026-10-09 - Task: 复检忽略规则与暂存区

### What was done

- 发现本机 IDE 的 workspace.xml 被重新暂存，已移出索引并保留本地文件。

### Testing

- 验证 18 个应忽略路径、13 个应保留路径，均符合预期。
- git ls-files -ci --exclude-standard 和 git ls-files .idea 均无输出；确认本地 workspace.xml 仍存在。
- Git 差异检查发现若干 S2 文件末尾空行提示，属于格式问题，与本轮忽略规则验证分别记录。

### Notes

- .idea/workspace.xml：撤销重新加入索引的状态，保留本地内容。
- progress.md：在末尾追加本轮检查及修复记录。
- 回滚：如需恢复本轮前的暂存状态，执行 git add -f -- .idea/workspace.xml；日志仅移除本轮末尾条目。未执行提交或推送。

## 2026-10-09 - Task: S3 LBAdaptiveSOM 背景建模与前景分割

### What was done

- 按原鱼类论文第 251–252 页实现 HSV 圆柱特征平方距离、扩大空间网格、跨像素邻域 Gaussian 更新、学习/在线阶段阈值和阴影判别；双视角分别维护背景模型。
- 复用 S2 视频读取、去畸变、中值滤波和 HSV/ROI 接口，输出二值前景掩膜、叠加图、逐帧统计、模型状态与可追溯运行记录；所有示例来源明确为 synthetic。
- 将论文公式与文字的差异、缺失参数、执行顺序和色相线性更新限制写入方法文档；本轮遵循用户阶段安排，不实现 S4 质心与跟踪。

### Testing

- 开工前执行固定验证脚本：21 passed in 0.45s；改动后执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：34 passed in 0.85s，包括 S0/S1/S2 回归与 13 项 S3 测试。
- 执行 `.\.venv\Scripts\python -m fish3d som-demo --config configs/synthetic_som.yaml --output outputs/synthetic_som_demo`：成功处理 18 帧 synthetic 视频；实测分割处理耗时约 7.29 秒，不据此声称实时性能。
- 校验 36 行逐视角 CSV、54 张二值掩膜、18 张叠加图、两个模型状态；前 3 帧无前景，其后鱼体中心为前景；全图掩膜与 ROI 原点拼接一致，模型形状/数值及来源元数据正确，视频与配置 SHA-256 匹配。
- 目视检查第 6 帧全图掩膜与叠加图，两个视角前景位置及 SYNTHETIC 标记正确。
- 独立执行 `.\.venv\Scripts\python -m fish3d segment-video --input outputs/synthetic_som_demo/synthetic_input.avi --config configs/synthetic_som.yaml --output outputs/synthetic_som_replay`：成功处理 18 帧；两次运行 72 张 PNG 文件逐字节相同，两个模型的数组与元数据相同。
- 执行 `python -m pip check`（使用项目虚拟环境）：无依赖冲突；`git diff --check` 无输出；`git check-ignore outputs/synthetic_som_demo/background_model_real.npz` 确认结果文件被忽略。

### Notes

- `src/fish3d/lbadaptive_som.py`：新增论文基准 SOM、参数校验、HSV 归一化/距离、阴影判别与模型保存。
- `src/fish3d/foreground_processing.py`：新增双视角分割及掩膜、叠加图、统计、模型与运行记录导出。
- `configs/synthetic_som.yaml`：新增明确标记 synthetic 的 S3 配置和参数来源说明。
- `src/fish3d/video_config.py`：新增默认值为 0 的合成视频背景空帧参数，保持原 S2 默认行为。
- `src/fish3d/video_io.py`：按配置生成初始无鱼背景帧，保留 synthetic 标记。
- `src/fish3d/__main__.py`：新增 som-demo 与 segment-video 命令。
- `tests/test_lbadaptive_som.py`：新增数学、初始化、阈值、阴影、空间邻域、色相、输入校验与合成视频集成测试。
- `docs/lbadaptive_som.md`：记录算法来源、参数口径、论文矛盾、工程约定、运行方法与限制。
- `docs/data_contract.md`：更新前景模块实现状态和二值掩膜合同。
- `README.md`：更新 S3 使用入口、输出与阶段状态。
- `progress.md`：仅在末尾追加本轮实现与验证记录，保留此前未提交的忽略规则复检记录。
- 已知限制：没有真实实验视频；首帧含鱼会被纳入初始背景，合成示例的 3 个空帧只用于受控测试；论文原始 HSV 线性更新在色相跨界处有偏差；缺失的学习率、邻域尺度等采用已注明的工程配置，尚待真实视频调参和评价。
- 回滚：执行 `git restore --source=0de9409 -- README.md docs/data_contract.md src/fish3d/__main__.py src/fish3d/video_config.py src/fish3d/video_io.py`；先执行 `git clean -n -- configs/synthetic_som.yaml docs/lbadaptive_som.md src/fish3d/foreground_processing.py src/fish3d/lbadaptive_som.py tests/test_lbadaptive_som.py` 核对清单，再将 `-n` 改为 `-f` 执行。日志仅移除本轮 S3 末尾条目，保留之前记录；ignored 的本地输出无需删除。未提交或推送。

## 2026-10-11 - Task: S4 单鱼质心提取与连续二维跟踪

### What was done

- 核对原论文第 252 页第 2.2 节、规划书质心要求与任务书单鱼范围，按用户阶段顺序实现 S4；将任务书阶段编号差异和未指定的关联算法记入文档。
- 从实际 SOM 掩膜计算连通域像素均值质心，提供配置化开/闭运算、连通性和面积筛选，转换到处理后的全帧像素坐标。
- 实现按真实时间戳的单目标位移门限与失踪时限；短缺失保留视角内编号，长失踪建立新轨迹段，缺失及拒绝坐标保留 NaN，不输出预测值。
- 复用 S3 分割产物，新增原始检测与二维跟踪 CSV、清理掩膜、质心叠加图、轨迹图和可追溯运行记录；合成示例增加两帧鱼消失，所有来源标为 synthetic。

### Testing

- 开工前执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：34 passed in 0.96s。改动后执行同一脚本：47 passed in 2.28s，包含 13 项新增 S4 测试及全部既有回归。
- 单元测试涵盖像素均值与空洞、ROI 偏移、面积筛选及并列、无前景/合法原点、形态学、连通性、静止/非均匀采样、二维跳变、短缺失/长失踪、输入合同、配置和合成视频集成。
- 执行 `.\.venv\Scripts\python -m fish3d tracking-demo --config configs/synthetic_tracking.yaml --output outputs/synthetic_tracking_demo`，成功处理 18 帧；核验 detections.csv 与 tracks_2d.csv 各 36 行、36 张清理掩膜、18 张跟踪叠加图及一张轨迹图。
- 检查第 0–2 帧以及第 8、9 帧无效坐标均为 NaN；两个视角各 13 个有效跟踪点，拒绝计数均为 0，短缺失前后各保持一个视角内编号；相对合成椭圆中心的最大偏差为 0.562446 px（仅合成验证）。
- 核验视频、配置及 S3 记录 SHA-256，二值掩膜值域、图像尺寸与逐行来源/单位；目视检查二维轨迹图与恢复后的第 10 帧叠加图，缺失区间不跨接，SYNTHETIC 标记保留。
- 独立执行 `.\.venv\Scripts\python -m fish3d track-video --input outputs/synthetic_tracking_demo/synthetic_input.avi --config configs/synthetic_tracking.yaml --output outputs/synthetic_tracking_replay`；两次运行的两份 CSV、54 张逐帧 PNG 及轨迹图共 57 个文件逐字节一致。
- 使用项目虚拟环境执行 pip check，无依赖冲突；git diff --check 无输出；git ls-files -ci --exclude-standard 无输出；git check-ignore 确认本轮输出仍被忽略。

### Notes

- `src/fish3d/centroid.py`：新增兼容现有接口的掩膜清理、连通域筛选与像素质心计算。
- `src/fish3d/tracking.py`：新增单鱼时间关联、NaN 缺失点与视角内轨迹段编号。
- `src/fish3d/tracking_processing.py`：新增复用 S3 结果的 S4 导出、叠加与二维图表流程。
- `configs/synthetic_tracking.yaml`：新增明确标记 synthetic 的 S4 参数与缺失帧示例。
- `src/fish3d/video_config.py`：新增默认空序列的 missing_frame_ids 配置及校验。
- `src/fish3d/video_io.py`：合成视频按配置跳过鱼体绘制，保持原示例默认行为。
- `src/fish3d/__main__.py`：新增 tracking-demo 与 track-video 命令。
- `tests/test_tracking_s4.py`：新增 S4 数学、关联、合同与输出验证。
- `docs/centroid_tracking.md`：说明论文依据、工程关联规则、输入输出、参数、运行与真实数据需求。
- `docs/data_contract.md`：更新 S4 实现状态、坐标系、缺失标记及编号口径。
- `README.md`：补充 S4 入口及验收后进入 S5 的阶段说明。
- `progress.md`：仅追加本轮实施与验证记录。
- 开工时已有的未跟踪文件 `baseDocs/基于轨迹提取的鱼类异常行为监测_李星辉.pdf` 保持原样，不纳入本轮修改。根目录没有实际 AGENTS.md 文件，本轮遵守用户会话内提供的执行规范。
- 已知限制：仅单鱼，最大连通域可能选中反光或合并目标；形态学会影响面积与边缘质心；视角内编号不证明两视角或物理身份；尚无真实视频验证。关联门限为工程配置，不是论文指定参数或行为阈值；本轮不包含 S5 双视角匹配与三维重建。
- 回滚：执行 `git restore --source=d30f475 -- README.md docs/data_contract.md src/fish3d/__main__.py src/fish3d/video_config.py src/fish3d/video_io.py`；先执行 `git clean -n -- configs/synthetic_tracking.yaml docs/centroid_tracking.md src/fish3d/centroid.py src/fish3d/tracking.py src/fish3d/tracking_processing.py tests/test_tracking_s4.py` 核对，再将 `-n` 改为 `-f` 执行。progress.md 只移除本轮末尾 S4 条目；上述回滚不涉及已有新论文或本地 ignored 输出。未提交或推送。

## 2026-10-11 - Task: S5 双视角对应与论文理想模型三维重建

### What was done

- 核对原论文第 250 页图 2、第 251 页式 (1) 及规划书/任务书的像素模型解释；明确几何参考 a 与 ROI 分界含义不同，单独配置镜面角度、完整图像几何参考和模型原点。
- 实现同帧同时间的单鱼双视角对应，增加已注明为工程设计的纵向偏差门限；分别保留两视角轨迹编号，不用编号相等证明物理身份。
- 实现论文式三维计算及代数逆投影，强制输出 model_px / paper_ideal_cartesian；缺失或匹配失败帧全部三维坐标为 NaN，编号变化分段绘制，未进行物理尺度换算。
- 从 S4 表导出对应记录、三维轨迹 CSV/图及可追溯参数记录；复用既有相机 JSON 读取/尺寸校验入口，区分配置的相机内参与尚未验证的上游去畸变/真实几何。
- S4 已验收但尚未提交，修改前在 ignored 的 outputs/s5_rollback_before 保存四个待修改文件的精确副本及 SHA-256，保留此前未提交的 S4 工作。

### Testing

- 开工前执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：47 passed in 1.91s。首轮 S5 测试 72 passed in 2.62s；补充依赖版本记录后的最终固定脚本验证为 72 passed in 2.63s，包含 25 项新增 S5 测试及 S0–S4 回归。
- 测试覆盖论文 45° 参考值、30° 独立数学参考、XYZ 独立变化的已知点逆投影/重建、60° 参数及非均匀时间、坐标原点、独立几何参考、缺失坐标、严格同步、纵向门限、视角编号不相等/变化、单位/来源/ROI 输入合同、重复行、全缺失及相机 JSON 尺寸校验。
- 执行 `.\.venv\Scripts\python -m fish3d geometry-demo --config configs/synthetic_geometry.yaml --output outputs/synthetic_geometry_demo`，完整 synthetic 视频链成功处理 18 帧，其中 13 帧对应成功，5 帧初始化空背景或消失帧输出全 NaN XYZ。
- 核验 matches.csv 与 trajectory_3d.csv 各 18 行、时间戳、来源/模型单位、对应状态、配对编号和输入/配置 SHA-256；逐有效帧核对结果等于输入实测质心按公式计算的 XYZ。相对合成椭圆与理想式的最大坐标偏差为 0.711123 model_px，仅为 synthetic 测试结果。
- 检查三维 PNG 可解码、尺寸为 1200×900，并目视确认坐标单位、SYNTHETIC/未验证模型标题和缺失区间断线。
- 独立执行 `.\.venv\Scripts\python -m fish3d reconstruct-tracks --input outputs/synthetic_tracking_demo/tracks_2d.csv --config configs/synthetic_geometry.yaml --output outputs/synthetic_geometry_replay`，使用已验收 S4 表成功得到 13/18 有效点；两份 CSV 与三维图逐字节等同完整 S5 示例。
- 项目虚拟环境 pip check 无依赖冲突；git diff --check 无输出；git ls-files -ci --exclude-standard 无输出；本轮输出及回滚副本仍被 Git 忽略。核验四个回滚副本 SHA-256 与保存时一致。

### Notes

- `src/fish3d/matching.py`：新增兼容原接口的单鱼同步及理想纵坐标一致性检查，保存失败原因。
- `src/fish3d/geometry.py`：新增可配置的论文理想像素模型、全 NaN 无效点、配对段编号与代数逆投影。
- `src/fish3d/reconstruction_processing.py`：新增 S4 CSV 输入校验、对应/三维导出、分段图表及来源/标定状态记录。
- `configs/synthetic_geometry.yaml`：新增明确标记 synthetic 的完整 S5 示例参数，几何参考与 ROI 分开配置。
- `src/fish3d/__main__.py`：新增 geometry-demo 和 reconstruct-tracks，保留已验收 S4 命令。
- `tests/test_geometry_s5.py`：新增 S5 数学、同步、合同、标定入口和输出测试。
- `docs/geometry_reconstruction.md`：记录公式依据、a 的含义差异、坐标/单位、工程对应规则、接口、运行及真实数据需求。
- `docs/data_contract.md`：补充模型单位、配对段编号、多段 CSV 使用及全 NaN 规则。
- `README.md`：补充 S5 命令、模型单位限制和待确认的 S6 阶段。
- `progress.md`：仅在末尾追加 S5 记录，保留已验收 S4 及此前历史。
- `outputs/s5_rollback_before/`：保存上述 README、数据合同、命令入口及日志的 S5 开工前副本和 sha256.json，仅本地 ignored 回滚资料。
- `outputs/source_review/paper_p250.png`：本地 ignored 的原论文第 250 页图示阅读副本；原始资料未修改。合成视频与所有派生测试产物均在 ignored 的 outputs 下。
- 已知限制：单鱼假设和纵坐标对齐尚待真实装置验证；model_px 数值不代表物理高度，is_valid 也不表示物理位置已验证。未实现标定光线/镜面反射、透视或水/玻璃折射重建；相机内参不能单独给该式赋予物理尺度。非 45° 测试仅为印刷公式的数值验证，没有真实三维误差或匹配准确率结论。
- 精确回滚 S5 并保留 S4：在仓库根目录执行 `$s5RollbackRoot = (Resolve-Path '.\outputs\s5_rollback_before').Path; @('README.md','docs/data_contract.md','src/fish3d/__main__.py','progress.md') | ForEach-Object { Copy-Item -LiteralPath (Join-Path $s5RollbackRoot $_) -Destination $_ -Force }`；先执行 `git clean -n -- configs/synthetic_geometry.yaml docs/geometry_reconstruction.md src/fish3d/matching.py src/fish3d/geometry.py src/fish3d/reconstruction_processing.py tests/test_geometry_s5.py` 核对，再将 `-n` 改为 `-f` 执行。本轮未提交或推送，不恢复到 S3 提交覆盖 S4。

## 2026-10-11 - Task: S6 规则行为识别与结果可视化

### What was done

- 核对原论文第 253 页 §2.4 和表 1，按原条件实现狂游（速度或角速度超阈值）、长时间漂浮水面（高度与持续时间）和跳出水面（高度超过水面），不预写模拟行为结果。
- 将高度、容差、持续时间、速度、角速度及采样连续性门限配置化；要求阈值单位、坐标系和来源逐条匹配输入，保留 S1 的三维中心差分/转向计算及已有 BehaviorRecognizer/BehaviorEvent 接口。
- 接入 S1/S5 单鱼三维 CSV，允许配对段编号变化；先按有效连续帧与真实时间分段再求运动特征，不跨缺失/超时求差分或补路径；漂浮持续时间遇缺失、跳帧、超时、编号变化或离开水面时重置。
- 导出全部帧的运动/规则表、独立规则事件表、分段三维图、运动/水面曲线、行为时间线以及输入/配置哈希和版本记录；未知狂游特征与无效坐标保留独立状态，不能当作确认正常。
- 明确水面容差、采样连续性和事件边界是工程约定；漂浮事件从首次超过持续阈值的观测开始，规则可以重叠。论文角速度阈值单位与时间定义未充分确认，继续使用既有 rad/s 口径并记录限制。
- 在 ignored 的 outputs/s6_rollback_before 保存四个共享文件的精确开工前副本和 SHA-256，保留已验收但尚未提交的 S4/S5；本轮不进入 S7。

### Testing

- 开工前执行固定脚本 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：72 passed in 3.57s。S6 首轮 100 passed in 4.96s，最终固定脚本为 100 passed in 4.75s，包含 28 项新增 S6 测试及 S0–S5 回归。
- 新增测试覆盖严格阈值与 OR 条件、NaN 未知、静止/零向量、XYZ 速度、独立转角/角速度参考、水面容差、规则重叠、不擅加漂浮低速条件、非均匀时间、缺失/漏帧/大时间间隔、编号切换、单位/来源合同、全缺失、CSV 顺序/布尔输入、导出/哈希及 synthetic 生成器来源保护。
- 实际运行 `.\.venv\Scripts\python -m fish3d behavior-demo --config configs/synthetic_behavior.yaml --output outputs/synthetic_behavior_demo`：生成 51 帧 synthetic 坐标，计算得到狂游 11–18 s、持续漂浮规则成立 36–44 s、跳出 45–50 s，各一项事件；水面接触从 20 s 开始，35 s 尚未严格超过 15 s，不回填为漂浮事件。所有事件仅为 rule_prediction。
- 实际运行 `.\.venv\Scripts\python -m fish3d analyze-behavior --input outputs/synthetic_geometry_demo/trajectory_3d.csv --config configs/synthetic_behavior_model.yaml --output outputs/synthetic_behavior_video_replay`：成功分析 S5 的 18 帧，保留 13 个有效点与 5 个无效点，按示例 32 model_px 水面阈值得到一段跳出规则预测；该值不是实际水面标定值。
- 独立核对两组运动表/规则表分别 51/18 行、帧号与时间戳对齐、synthetic 来源和一致单位；无效帧速度/角速度/速度矢量为 NaN且行为均未检出；输入/配置 SHA-256 与文件内容一致，事件来源及预测类型正确，真实准确率验证标记为 false。
- 两组共六张 PNG 均可解码：三维图 1200×900、运动曲线 1350×1200、时间线 1350×525；目视检查合成运动/高度曲线及 S5 回放的无效/未知状态时间线，标题明确 SYNTHETIC 与未经过真实验证。
- pip check 报告 No broken requirements found；git diff --check 与 git ls-files -ci --exclude-standard 无输出；确认结果、回滚副本仍被 Git 忽略，四个回滚副本哈希均与保存时一致。进度日志原内容作为字节前缀保留，仅末尾追加。

### Notes

- `src/fish3d/behavior.py`：新增配置、三项论文条件、连续观测判断、逐帧评价状态和兼容原接口的事件识别。
- `src/fish3d/behavior_processing.py`：新增轨迹 CSV 输入、连续段运动复用、synthetic 坐标构造、结果表与来源/版本/哈希记录。
- `src/fish3d/behavior_visualization.py`：新增分段三维图、速度/角速度/水面曲线与独立规则/未知状态时间线。
- `configs/synthetic_behavior.yaml`：新增明确 synthetic 的 51 帧分段坐标构造参数和三类规则验证阈值。
- `configs/synthetic_behavior_model.yaml`：新增明确 synthetic / model_px 的 S5 视频轨迹回放参数，不赋予物理尺度。
- `tests/test_behavior_s6.py`：新增 S6 核心规则、时间/缺失处理、单位与来源合同及输出测试。
- `src/fish3d/__main__.py`：新增 behavior-demo 与 analyze-behavior，保留既有入口。
- `docs/behavior_analysis.md`：记录论文依据、时间/单位歧义、工程约定、配置与接口、运行/输出和真实视频/标签需求。
- `docs/data_contract.md`：补充 S6 单鱼多轨迹段输入、观察事件区间、逐帧评价有效性和规则预测合同。
- `README.md`：补充 S6 状态、入口、文档和待确认/取得真实资料后进入 S7 的阶段说明。
- `progress.md`：仅追加本轮实施、验证和回滚说明，不改写既有阶段历史。
- `outputs/s6_rollback_before/`：上述四个共享文件的开工前副本与哈希，仅本地 ignored 资料；示例与派生结果也在 ignored 的 outputs 中。原始资料、已有新论文和 S4/S5 专有文件保持原样。
- 已知限制：尚无真实视频/人工标签，规则阈值没有实验校准，不能报告识别准确率；S5 model_px 仍非物理高度/速度。输入保持单鱼每帧一行；无轨迹插值、噪声平滑或实验几何纠正；仅质心高度的跳出/漂浮条件不能证明鱼体整体越过水面或生物学异常。事件记录为观测区间，不外推真实起止，角速度口径须在真实阈值确定前统一。
- 精确回滚 S6 并保留 S4/S5：在仓库根目录执行 `$s6RollbackRoot = (Resolve-Path '.\outputs\s6_rollback_before').Path; @('README.md','docs/data_contract.md','src/fish3d/__main__.py','progress.md') | ForEach-Object { Copy-Item -LiteralPath (Join-Path $s6RollbackRoot $_) -Destination $_ -Force }`；先执行 `git clean -n -- configs/synthetic_behavior.yaml configs/synthetic_behavior_model.yaml docs/behavior_analysis.md src/fish3d/behavior.py src/fish3d/behavior_processing.py src/fish3d/behavior_visualization.py tests/test_behavior_s6.py` 核对，再将 `-n` 改为 `-f` 执行。本轮未提交或推送，不恢复到 S3 提交覆盖 S4/S5。

## 2026-10-13 - Task: 确认五鱼实验方向并建立多目标二维检测与跟踪预览

### What was done

- 按用户修正确定最终多鱼需求、实际群体数量 5 及左实体/右镜像；将该视频的实体 ROI 放在左侧，矩形边界由抽帧初步估计并明确标记待确认，不使用论文的左右区域或装置几何常量。
- 扩展质心提取以返回全部面积合格连通域，原最大连通域入口保持语义；保留原论文 LBAdaptiveSOM 和已有预处理，不以深度学习或替代分割算法跳过论文路线。
- 增加基于真实时间的恒速预测、速度/预测误差门限和全局分配；大连通域疑似合并时排除并输出缺失/遮挡 NaN，短失踪保留段编号，长失踪结束段。五鱼数量只限制同时活动的轨迹，不补出五个检测或把视角内段号当作物理身份。
- 新增独立的限长、单视角多鱼预览入口，缩小 ROI 分割后恢复完整图像像素坐标；导出全部原始候选、逐轨迹观测、逐帧诊断、掩膜、原尺度叠加图、轨迹图、模型和来源/单位/哈希记录。
- 新增明确 synthetic 的五鱼椭圆视频与独立已知坐标示例，拒绝标作 experimental；真实短片段输出标为 experimental，不给出没有人工标签支持的准确率。
- 添加 SciPy 线性分配依赖，实际安装后执行验证；同步说明真实预览失败现象和旧单鱼 S5/S6 入口仍待多鱼适配。未改核心数据协议或未经确认的物理重建参数。
- 开工前在 ignored 的 outputs/multifish_rollback_before 保存六个待修改共享文件的精确副本与 SHA-256；基线提交为 b9d0288，保留所有此前工作。

### Testing

- 基线固定脚本 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1` 为 100 passed in 7.67s。首轮新增测试为 120 passed / 2 failed in 15.89s：测试遗漏 ForegroundMask 必填 ROI 参数，且误把面积排序的轨迹段编号等同构造鱼标签；修正测试合同并按初始化实测位置与独立真值建立一一映射，检查后续身份保持。最终固定脚本为 122 passed in 15.79s，包含 22 项新增测试及全部既有阶段回归。
- 测试覆盖五个连通域、最大组件兼容、候选顺序变化、非均匀时间与 XY 位移、五鱼数量不补齐、交叉/合并遮挡、全局最大可行配对、短失踪/长失踪、速度与预测门限、输入与参数、尺度转换、限长运行、synthetic 来源保护和完整 SOM 输出链。
- 执行 `.\.venv\Scripts\python -m pip install -e '.[test]'`，实际安装 scipy 1.17.1；pip check 为 No broken requirements found。
- 实际执行 `.\.venv\Scripts\python -m fish3d multi-tracking-demo --config configs/synthetic_multi_tracking.yaml --output outputs/synthetic_multi_tracking_demo`：20 帧、前三帧无鱼、15 帧五个有效观测、2 帧四个有效观测；独立真值共 100 行，算法表 83 个检测、85 个轨迹观测，其中 83 有效、2 个明确缺失，共 5 个连续段编号，观测质心按独立已知坐标验证。
- 实际执行 `.\.venv\Scripts\python -m fish3d track-multi-video --input data/raw/experiment_001.mp4 --config configs/experiment_001_multi_preview.yaml --output outputs/experiment_001_multi_preview`：处理 60 帧、0.0–5.9 s，解码器时间戳 60 帧有效；本地记录耗时 24.425 s，仅为本次预览运行耗时，不声称全片性能。
- 真实预览记录 758 个面积合格候选（不是 758 条鱼）、290 条轨迹观测，其中 205 有效；有效轨迹数直方图为 {0:1,1:2,2:9,3:18,4:19,5:11}。状态包括 initialized 16、tracked 189、missing 72、lost 11、occluded 2；累计 16 个段编号显示轨迹断裂，不能报告五鱼稳定跟踪成功或身份切换准确率。
- 独立检查两组 CSV 帧计数、候选/轨迹计数一致、同帧同编号唯一、来源区分、px/processed_full_frame 单位、有效观测不超过 5、无效点全 NaN且面积 0，视频/配置 SHA-256 和模型来源/处理帧数一致。两组共 240 张逐帧 PNG 全部可解码且尺寸正确；真实缩放掩膜为 92×128，原尺度叠加图为 960×800。
- 目视检查真实第 30/59 帧叠加：存在气泡、缸壁/底部及边缘前景候选，真实五鱼身份尚未持续保持；本次真实五鱼稳定跟踪未通过验收。视角确认和群体数量不等同目标识别参考标签。
- git diff --check 无输出；git ls-files -ci --exclude-standard 无输出；原视频、实验/synthetic 派生结果及回滚副本仍被 Git 忽略；六个回滚副本哈希与保存时一致，progress.md 原内容作为字节前缀保留。

### Notes

- `src/fish3d/centroid.py`：新增全部合格连通域输出，原 extract 通过首项保留最大组件行为。
- `src/fish3d/multi_tracking.py`：新增多鱼配置、恒速预测/门限/全局分配、合并候选处理及带状态的二维段观测。
- `src/fish3d/multi_tracking_processing.py`：新增原算法限长预览、缩放坐标恢复、全部候选/轨迹/帧表、图像/模型记录及 synthetic 构造。
- `src/fish3d/__main__.py`：新增 multi-tracking-demo 和 track-multi-video，保留原阶段命令。
- `configs/experiment_001_multi_preview.yaml`：新增真实五鱼、左实体视角、待确认 ROI 和前 60 帧预览参数，无物理标定猜测。
- `configs/synthetic_multi_tracking.yaml`：新增五个合成目标与短失踪的图像、跟踪和限长参数。
- `tests/test_multi_tracking.py`：新增多目标、遮挡、身份/时间、数量约束、尺度和完整原算法链测试。
- `pyproject.toml`：添加 scipy>=1.11,<2，供线性分配使用。
- `docs/multi_fish_tracking.md`：记录确认的实验信息、工程扩展、配置/坐标、入口与输出、实际失败现象和后续多鱼三维缺口。
- `docs/data_contract.md`：增加独立多鱼二维表、同帧多编号、缺失及尺度合同，明确原单鱼后续入口不接收该表。
- `README.md`：补充最终五鱼要求与真实实体视角预览命令/限制，不声称完整多鱼系统交付。
- `progress.md`：仅追加本轮结果、真实验收缺口和回滚说明。
- 已知问题：真实短片段的气泡/缸壁候选与背景初始化导致轨迹断裂，原尺度 ROI 边界仍待确认；缩小会损失鱼体细节。当前只有实体二维预览，没有真实标签评价、多鱼跨视角对应、逐鱼三维/行为接入或全片验证。下一最小工作是处理已观察到的真实前景干扰与轨迹断裂，不能直接跳到五鱼三维行为结论。
- 精确回滚本轮：在仓库根目录执行 `$multiRollbackRoot = (Resolve-Path '.\outputs\multifish_rollback_before').Path; @('README.md','docs/data_contract.md','src/fish3d/__main__.py','src/fish3d/centroid.py','pyproject.toml','progress.md') | ForEach-Object { Copy-Item -LiteralPath (Join-Path $multiRollbackRoot $_) -Destination $_ -Force }`；先执行 `git clean -n -- configs/experiment_001_multi_preview.yaml configs/synthetic_multi_tracking.yaml docs/multi_fish_tracking.md src/fish3d/multi_tracking.py src/fish3d/multi_tracking_processing.py tests/test_multi_tracking.py` 核对，再将 `-n` 改为 `-f` 执行。恢复依赖文件后可执行 `.\.venv\Scripts\python -m pip install -e '.[test]'` 重建包元数据；额外已安装的 SciPy 可保留，不影响旧算法。本轮未提交或推送。

## 2026-10-15 - Task: 新增两份实验视频接入及气泡/短暂候选的受控优化

### What was done

- 检查新增 EVE2/EVE3 与原视频的首段、中段、末段附近画面和解码信息；两份新增视频均为 2448×2048、约 10 fps，报告时长分别约 1790.647/1853.195 s，仍有暗鱼体、气泡和边缘干扰。
- 提供适配新增尺寸的初步实体/镜像 ROI、像素关联门限与原算法预览配置；新增视频鱼数和视角仍待用户确认，五鱼容量和对应方向明确标为 pending，不作为已确认实验事实。
- 在不替换或改动论文 SOM 的前提下增加可关闭的像素二阶矩主次轴比筛选，记录面积筛选前后的组件特征和拒绝数量；真实对照表明形状筛选导致轨迹更碎，保留实验分支，默认关闭。
- 增加可关闭的连续观测确认：短暂候选不立即获得正式编号；三帧确认仅导出当前实测点，不回填未确认点或预测点；未确认候选不占正式容量，缺失/跳帧中断确认，原默认一帧行为保留。
- 增加严格的一变量对照脚本：要求视频哈希、视角、时间范围和尺度相同，配置仅改变指定参数，且 SOM 掩膜逐帧逐字节一致；输出诊断数量，不以段数减少替代准确率评价。
- 生成三视频各两帧的原尺寸人工复核图、前后预测对照，以及 30 个尚未标注的空白反馈槽位；整理交给实验人员的照明、稳定机位、供氧记录、背景参考、时间信息和快行为采样需求。
- 保留本轮开始前已有全部未提交工作，七个本轮共享文件的精确副本/哈希保存于 ignored 的 outputs/optimization_20261015/rollback_before；无依赖新增、无原视频改写、无多鱼三维或真实准确率完成声明。

### Testing

- 先实际运行两个秒级可复现失败探针：5 个不同方向鱼形目标加 10 个圆气泡，原组件提取得到 15 而非 5；单帧噪声原跟踪器立刻获得 1 个正式编号，随后缺失。它们分别驱动当前组件提取和多目标跟踪的真实代码路径，不是固定模拟输出。
- 先写形状测试，6 项因缺少新接口/诊断字段失败；实现后连同原 S4/多鱼定向回归为 41 passed in 9.49s。确认机制先写 5 项测试失败，实现后连同原多鱼回归为 27 passed in 8.07s；补充超过容量的持续候选检查后，确认测试 6 passed in 0.50s。
- 首次完整固定脚本为 133 passed in 17.18s；增加容量用例后，最终执行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1` 为 134 passed in 11.55s，含 12 项本轮新增用例和此前 122 项回归。
- 三个视频分别运行 baseline、shape、confirmed 共九次 `track-multi-video`，每次处理同一视频开头 60 帧，累计 540 次帧处理、180 个不同视频帧时刻；仅为约 6 s 预览，不代表约半小时全片验收。命令配置与目录见 docs/multi_fish_tracking.md。
- 独立形状门限 1.0→1.8：候选数分别 758→581、879→551、1241→704，但正式段数 16→21、14→18、13→16，故没有把它设为默认优化或声称真实气泡误检率降低。
- 独立确认帧数 1→3，形状仍关闭：正式段数分别 16→15、14→12、13→8；有效实测观测数 205→181、194→174、201→193。确认产生延迟和少量短时目标丢弃，这些数字不代表物理身份准确率。
- `scripts/compare_multi_runs.py` 实际执行三组 shape 与三组 confirmation 对照，各对的原始 SOM 掩膜逐帧逐字节一致；输出输入/配置哈希及完整诊断值。当前默认一帧跟踪器重放三组旧基线检测表，290/285/290 行轨迹的帧号、时间、XY、面积、有效性、编号和状态逐项完全相同，证明默认兼容。
- 独立核验九次运行的视频/配置 SHA-256、每次 60 帧、组件/候选/有效轨迹计数一致、同帧同编号唯一、最多五条正式有效观测、缺失坐标全 NaN且面积 0、experimental 来源、px/processed_full_frame 输出及未验证标记。1620 张逐帧 PNG 全部可解码且尺寸正确，12 张人工反馈 JPEG 可解码；30 个反馈槽位全部保持 pending_human、XY 空白，未被当作人工标签。
- 目视检查 EVE2 第 59 帧和 EVE3 第 30 帧前后预测图：气泡/扰动仍可能被持续跟踪、暗鱼体仍有漏检，五鱼物理身份未稳定验证。没有人工参考标签，不能宣称召回、ID 切换率或真实行为准确率改善。
- pip check 无依赖冲突；git diff --check 与 git ls-files -ci --exclude-standard 无输出。两份新增原视频、全部运行结果和反馈模板仍被 Git 忽略；七个回滚副本哈希一致，旧 progress.md 字节内容保留为完整前缀。

### Notes

- `src/fish3d/centroid.py`：增加默认关闭的轴比门限与面积/形状诊断，原最大组件与默认候选语义兼容。
- `src/fish3d/multi_tracking.py`：增加默认一帧兼容、可配置三帧确认、内部暂存和已确认优先的关联管理，不输出暂存预测坐标或消耗正式段号。
- `src/fish3d/multi_tracking_processing.py`：增加组件特征表、面积/形状/暂存帧统计、有效配置及算法版本记录。
- `scripts/compare_multi_runs.py`：新增严格校验同视频同分割、仅改变一个参数的对照汇总命令。
- `tests/test_component_shape.py`：新增旋转不变的鱼形/圆形构造验证、默认兼容、非法门限和退化组件测试。
- `tests/test_track_confirmation.py`：新增单帧噪声、五鱼持续候选、跳帧重置、容量与确认参数测试。
- `configs/eve2_multi_preview.yaml`、`configs/eve3_multi_preview.yaml`：新增两份高分辨率真实视频的基线预览配置，鱼数/视角待确认、ROI 初估。
- `configs/experiment_001_multi_shape.yaml`、`configs/eve2_multi_shape.yaml`、`configs/eve3_multi_shape.yaml`：分别新增单独改变轴比门限的实验配置，实测未作为默认优化。
- `configs/experiment_001_multi_confirmed.yaml`、`configs/eve2_multi_confirmed.yaml`、`configs/eve3_multi_confirmed.yaml`：分别新增单独改变连续确认帧数、保持形状关闭的试跑配置。
- `docs/multi_fish_tracking.md`：补充实际新增视频信息、两项实验方法/代价、真实负结果和完整受控对照运行方式。
- `docs/video_feedback.md`：新增具体人工复核帧、原坐标标注约定、空白槽位说明和交给实验人员的采集要求。
- `docs/data_contract.md`：补充可选组件形状、局部掩膜特征与正式/暂存轨迹合同，不改核心接口数据结构。
- `README.md`：更新真实短片段接入状态，增加新视频确认配置入口和人工反馈文档。
- `progress.md`：仅追加本轮实验、负结果、验证及精确回滚记录，不重写既有历史。
- 本轮源代码/正式文档改动共上述 19 个文件；前一轮未提交的依赖、命令入口、原多鱼配置与测试均保留。所有新增原视频仅读取，派生对照/人工复核资料位于 ignored 的 outputs/optimization_20261015。
- 研究限制：确认机制也可能稳定气泡等错误目标；形状筛选会拒绝迎面或弯曲的真实鱼。新增视频鱼数/映射、无鱼背景和标定文件尚待人工反馈，不能将五鱼容量、离散槽位或算法段号当真值。下一最小动作是确认新增视频信息，并在已给的原尺寸第 30/59 帧标出鱼/气泡及遮挡，再进行标签驱动的分割优化；不跳到三维/行为结论。
- 精确回滚本轮并保留上轮未提交工作：在仓库根目录执行 `$optimizationRollbackRoot = (Resolve-Path '.\outputs\optimization_20261015\rollback_before').Path; @('src/fish3d/centroid.py','src/fish3d/multi_tracking.py','src/fish3d/multi_tracking_processing.py','README.md','docs/data_contract.md','docs/multi_fish_tracking.md','progress.md') | ForEach-Object { Copy-Item -LiteralPath (Join-Path $optimizationRollbackRoot $_) -Destination $_ -Force }`；先执行 `git clean -n -- configs/eve2_multi_preview.yaml configs/eve3_multi_preview.yaml configs/experiment_001_multi_shape.yaml configs/eve2_multi_shape.yaml configs/eve3_multi_shape.yaml configs/experiment_001_multi_confirmed.yaml configs/eve2_multi_confirmed.yaml configs/eve3_multi_confirmed.yaml tests/test_component_shape.py tests/test_track_confirmation.py scripts/compare_multi_runs.py docs/video_feedback.md` 核对，再将 `-n` 改为 `-f` 执行。本轮未提交或推送，不用 git restore HEAD 覆盖前一轮工作。

## 2026-10-15 - Task: 按人工确认修正新增视频鱼数并建立圈图反馈目录

### What was done

- 记录用户确认：EVE2/EVE3 各有 3 条鱼，原五条中两条损耗；experiment_001 保持已确认的 5 条。将两视频各三个配置变体的数量改为 3，数量来源标记为 confirmed_by_user，保留现有 ROI/方向判断状态和算法参数。
- 建立 data/annotations 作为圈图输入目录，说明视频简称、帧号、marked 命名和原尺寸标注方式；创建按 5/3/3 数量分配的 22 槽空白模板，保留原 30 槽历史模板和原图。
- 同步说明旧优化表是在五鱼容量假设下产生，不能作为已确认三鱼条件的验收结果。旧输出的配置快照/哈希保留，当前 YAML 已更新；本轮只做数量与反馈路径修正，没有再次调参或重新处理真实视频。
- 在 ignored 的 outputs/count_correction_20261015/rollback_before 保存十一份开工前副本及哈希，保留此前所有未提交工作。

### Testing

- 实际加载两视频六份 YAML，通过 MultiTrackingConfig/VideoConfig 校验，均为 experimental、expected_fish_count=3、confirmed_by_user；原 experiment_001 配置仍为 5。
- 新模板 annotation_template_confirmed_counts.csv 共 22 个槽位，原视频两帧各 5 个、新视频各两帧各 3 个；全部为 pending_human、XY 留空，不作为人工标签或识别结果。
- 执行固定脚本 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1`：134 passed in 11.39s；没有增加只复述配置值的测试。
- git diff --check 无输出；git check-ignore 确认 data/annotations/eve2_frame_000059_marked.jpg 命中忽略规则；十一份回滚副本哈希保持一致，原日志内容完整保留为字节前缀。

### Notes

- `configs/eve2_multi_preview.yaml`：将 EVE2 面积基线数量修正为人工确认的 3。
- `configs/eve2_multi_shape.yaml`：将 EVE2 形状试验数量修正为人工确认的 3。
- `configs/eve2_multi_confirmed.yaml`：将 EVE2 连续确认试验数量修正为人工确认的 3。
- `configs/eve3_multi_preview.yaml`：将 EVE3 面积基线数量修正为人工确认的 3。
- `configs/eve3_multi_shape.yaml`：将 EVE3 形状试验数量修正为人工确认的 3。
- `configs/eve3_multi_confirmed.yaml`：将 EVE3 连续确认试验数量修正为人工确认的 3。
- `README.md`：区分原视频 5 条与新增视频各 3 条，提供圈图目录并标记旧表适用范围。
- `docs/data_contract.md`：说明鱼数按视频分别配置，避免把项目多鱼要求固定理解为每片五条。
- `docs/multi_fish_tracking.md`：记录确认后的数量及旧五鱼容量表的历史性质和复算条件。
- `docs/video_feedback.md`：新增圈图路径和命名，改用数量修正后的 22 槽模板。
- `progress.md`：仅追加本轮数量确认、配置验证与回滚说明。
- `data/annotations/`：新增本地圈图目录，受 data/ 忽略规则保护；其中人工图像属于用户输入资料。
- `outputs/optimization_20261015/manual_review/annotation_template_confirmed_counts.csv`：新增 22 槽待人工填写模板，原 30 槽文件保留。
- 当前边界：旧五鱼容量的跟踪结果尚未按三鱼配置重跑；新增方向仍按抽帧判断，ROI 和物理标定未确认。等待圈图后继续基于真实三鱼与人工参考优化，不能将旧五鱼试跑直接当作三鱼验证。
- 精确回滚本轮：在仓库根目录执行 `$countRollbackRoot = (Resolve-Path '.\outputs\count_correction_20261015\rollback_before').Path; @('configs/eve2_multi_preview.yaml','configs/eve2_multi_shape.yaml','configs/eve2_multi_confirmed.yaml','configs/eve3_multi_preview.yaml','configs/eve3_multi_shape.yaml','configs/eve3_multi_confirmed.yaml','README.md','docs/data_contract.md','docs/multi_fish_tracking.md','docs/video_feedback.md','progress.md') | ForEach-Object { Copy-Item -LiteralPath (Join-Path $countRollbackRoot $_) -Destination $_ -Force }`。回滚保留人工反馈目录与本地模板；本轮未提交或推送。

## 2026-10-15 - Task: 按最新人工更正统一真实实验视频为四条鱼

### What was done

- 用户明确更正“没有3条鱼，一直是4条”：撤销此前五条、三条及损耗的实验记录，experiment_001、EVE2/EVE3 和最新新增的 a3d72…_raw/a8d940… 两段视频均按四条记录。九份已有真实视频配置统一为 4，其他算法、ROI、尺度和时间参数不变。
- 同步当前说明与实验配置回归断言，移除运行清单中固定“五个观测”的错误措辞。保留 synthetic 五鱼示例及对应测试，继续验证可配置数量，不将合成数量当作实验事实。
- 生成三个已有视频各两帧、每帧四个槽位的 24 行待标注模板，全部坐标留空且 pending_human；旧 22/30 槽模板、历史运行清单和旧日志保持原样，明确旧五鱼容量结果不能用于四鱼验收。
- 最新两段仅记录已确认鱼数与先前抽样信息，本轮未新增 ROI 或重跑视频。修改前十六份文件的精确副本及 SHA-256 保存在 outputs/population_four_20261015/rollback_before。

### Testing

- 实际加载九份真实 YAML，经 VideoConfig/MultiTrackingConfig 校验全部为 experimental、expected_fish_count=4；与备份比较解析后的文档，除该数量字段外完全一致。synthetic_multi_tracking.yaml 仍为 5。
- 对上述九份配置逐一运行 synthetic 六个持续候选的真实跟踪入口，确认正式有效观测不超过四个、确认完成后恰有四个；随后空候选帧均输出四个缺失观测，XY 全 NaN，不虚构有效点。这是构造输入验证，不是真实视频检测准确率。
- 执行 powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1：134 passed in 13.57s。
- 新模板 24 行、六组视频/帧、每组四个不同索引；全部 pending_human、XY 空白。十六份回滚副本哈希一致；追加前 progress.md 与备份字节一致。
- 标准 git diff --check 对原有 CRLF 配置行报行末空白；保留原文件换行，通过单次命令 git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check，无输出，不改 Git 配置。git ls-files -ci --exclude-standard 无输出；git check-ignore 确认新验证报告和模板被忽略。
- 检查证据保存在 outputs/population_four_20261015/correction_checks.json。没有真实视频重跑或全片验证，也没有新增依赖。

### Notes

- configs/experiment_001_multi_preview.yaml：原视频基线数量由五改四，并修正人工确认注释。
- configs/experiment_001_multi_shape.yaml：原视频形状对照数量由五改四。
- configs/experiment_001_multi_confirmed.yaml：原视频连续确认数量由五改四。
- configs/eve2_multi_preview.yaml：EVE2 基线数量由三改四，并修正注释。
- configs/eve2_multi_shape.yaml：EVE2 形状对照数量由三改四，并修正注释。
- configs/eve2_multi_confirmed.yaml：EVE2 连续确认数量由三改四。
- configs/eve3_multi_preview.yaml：EVE3 基线数量由三改四，并修正注释。
- configs/eve3_multi_shape.yaml：EVE3 形状对照数量由三改四，并修正注释。
- configs/eve3_multi_confirmed.yaml：EVE3 连续确认数量由三改四。
- README.md：统一当前实验四鱼事实，撤销旧数量并说明历史运行不作为当前验收。
- docs/data_contract.md：纠正实验群体数量，保留原多鱼数据合同。
- docs/multi_fish_tracking.md：纠正当前数量和容量说明，保留五鱼 synthetic 结果和错误容量下的历史诊断。
- docs/video_feedback.md：记录最新两段也为四鱼、尚未独立运行，指向新模板，并撤销旧模板数量依据。
- src/fish3d/multi_tracking_processing.py：将运行清单中的固定五鱼措辞改为配置数量说明，算法不变。
- tests/test_multi_tracking.py：现有真实配置来源保护用例的数量断言改为四，synthetic 测试不变。
- progress.md：仅追加本轮更正、测试和回滚记录，历史内容不改写。
- outputs/population_four_20261015/manual_review/annotation_template_four_fish.csv：新增 24 行无坐标待人工确认模板，Git 忽略。
- outputs/population_four_20261015/correction_checks.json：保存配置、容量/缺失行为与实际 pytest 验证结果，Git 忽略。
- outputs/population_four_20261015/rollback_before/：保存本轮十六份正式文件的改前副本和 files.json 哈希索引，Git 忽略。
- 回滚方式（仓库根目录 PowerShell）：`$fourFishRollbackRoot = (Resolve-Path '.\outputs\population_four_20261015\rollback_before').Path; $fourFishRollbackFiles = Get-Content -LiteralPath (Join-Path $fourFishRollbackRoot 'files.json') -Raw | ConvertFrom-Json; $fourFishRollbackFiles.PSObject.Properties.Name | ForEach-Object { Copy-Item -LiteralPath (Join-Path $fourFishRollbackRoot $_) -Destination $_ -Force }`。此命令恢复十六份正式文件（包括改前日志），保留 ignored 的验证证据和模板；恢复后数量回到已被用户否定的旧值，仅用于撤销本轮施工，不作为真实数量证明。未提交或推送。

## 2026-10-15 - Task: 明确五条损耗一条后的四条阶段并撤销三条记录

### What was done

- 用户最终澄清为最初五条、损耗一条后四条，从未有过三条阶段。纠正上一轮“始终四条”的错误理解；原 experiment_001 按最初五条，EVE2/EVE3 及最新 a3d72…_raw/a8d940… 两段按后续四条记录。损耗确切时间未知，不推断视频内具体转变帧。
- 将 experiment_001 三份配置和已有回归断言恢复为五条；后续六份配置保持四条、其余参数不变。保留上一轮通用数量说明以及全部算法代码，不改写历史运行结果。
- 当前文档统一说明数量阶段：原视频历史五鱼容量正确，EVE2/EVE3 历史五鱼容量错误，后者尚未按四鱼重跑；原视频数量正确也不证明检测或身份准确率。
- 生成 26 个待标注槽位：原视频两帧各五个、EVE2/EVE3 各两帧各四个，全部 pending_human、XY 空白。旧 22/24/30 槽模板保留并注明不再使用。本轮改前九份正式文件副本及哈希保存在 outputs/population_history_20261015/rollback_before。

### Testing

- 实际加载九份真实配置，数量分别为 5/4/4（三组各三份），全部来源 experimental；原视频三份配置与本轮备份的 YAML 比较，除 expected_fish_count 恢复为 5 外完全相同。synthetic 五鱼配置不变。
- 执行 powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1：134 passed in 14.07s。
- 验证新模板有 26 行、六组视频/帧、组内索引唯一，所有坐标为空且 label_status=pending_human；不作为人工标签或检测结果。验证九份回滚副本 SHA-256 一致，追加前 progress.md 与备份字节一致。
- git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check 通过；沿用 CRLF 识别选项，保留原换行与编码，不修改 Git 配置。git check-ignore 确认新报告和新模板受 outputs/ 忽略规则保护。
- 验证证据位于 outputs/population_history_20261015/correction_checks.json。本轮只更正数量阶段和使用说明，没有重新处理实验视频或新增依赖。

### Notes

- configs/experiment_001_multi_preview.yaml：原视频基线数量恢复为五，并纠正注释。
- configs/experiment_001_multi_shape.yaml：原视频形状对照数量恢复为五。
- configs/experiment_001_multi_confirmed.yaml：原视频连续确认数量恢复为五。
- tests/test_multi_tracking.py：原视频配置与实验来源保护用例的数量断言恢复为五。
- README.md：明确五条损耗一条后四条、无三条阶段，并区分原视频与后续视频的历史数量适用性。
- docs/data_contract.md：按视频记录最初五条与后续四条，不改变数据接口。
- docs/multi_fish_tracking.md：纠正群体阶段、配置上限和历史运行解释，保留实际算法诊断数据。
- docs/video_feedback.md：记录损耗一条、无三条阶段，指向新的 26 槽模板并注明旧模板不再使用。
- progress.md：仅追加本轮最终澄清及验证，旧数量误记作为历史施工记录保留，以本条为准。
- outputs/population_history_20261015/manual_review/annotation_template_population_history.csv：新增按 5/4/4 分配的 26 槽空白模板，Git 忽略。
- outputs/population_history_20261015/correction_checks.json：保存实际配置、模板和 pytest 结果，Git 忽略；上一轮报告仅代表当时配置。
- outputs/population_history_20261015/rollback_before/：保存九份改前文件及哈希索引，Git 忽略。
- 精确回滚（仓库根目录 PowerShell）：`$populationHistoryRollbackRoot = (Resolve-Path '.\outputs\population_history_20261015\rollback_before').Path; $populationHistoryRollbackFiles = Get-Content -LiteralPath (Join-Path $populationHistoryRollbackRoot 'files.json') -Raw | ConvertFrom-Json; $populationHistoryRollbackFiles.PSObject.Properties.Name | ForEach-Object { Copy-Item -LiteralPath (Join-Path $populationHistoryRollbackRoot $_) -Destination $_ -Force }`。恢复九份正式文件及改前日志，保留 ignored 交付和备份；恢复的是上一轮“始终四条”的错误状态，仅供施工撤销，不作为实验事实。此前未提交的其他修改完整保留；本轮未提交或推送。

## 2026-10-15 - Task: 接入两段新增四鱼视频并完成短片段二维复核

### What was done

- 继续用户已确认的两段四鱼视频 a3d72d0123ef9a90d191f8ee25f5648f_raw.mp4（2448×2048、约 10 fps、报告 2013.946 s）和 a8d94062481beee3174300508337833c.mp4（960×800、10 fps、报告 1800.2 s）。最初 experiment_001 五条、损耗一条后后续四条的记录保持不变，没有三条阶段。
- 分别读取首帧、中段和约 95% 处画面，建立独立矩形实体/镜像 ROI 配置，扩大上部及底部覆盖，不直接套用旧框。边界来源明确为抽样初估，尚非标定；镜像本轮仅配置边界，实际只运行实体视角。
- 两份配置保留原论文 SOM、中值滤波/HSV 和已有多目标关联，形状筛选关闭，连续三帧确认，四鱼数量只限制同时活动轨迹，不补齐鱼数。算法源码、依赖及此前全部配置不改；原三视频各配置仍为 5/4/4。
- 实际通过现有 CLI 各处理开头 60 帧，保存实验来源 CSV、原尺寸叠加图、二值掩膜、模型、轨迹图和运行清单；生成新增两段第 30/59 帧共八张原图/预测复核图，供人工判读。
- 目视确认多个正式编号落在气泡或底部反射上，暗鱼体仍有漏检。完成的是短片段可运行性、输出合同和问题定位，稳定四鱼跟踪未通过验收；不报告真实准确率或算法改善，不将四个有效观测当作四条正确鱼。

### Testing

- 固定验证脚本 powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1 实际结果：134 passed in 13.85s。本轮是独立输入配置适配，不新增仅复述配置常数的测试。
- 两次 track-multi-video 均正常退出：a3d72_raw 60 帧、0–5.869 s、1285 个合格候选观测、9 个正式段、140 个有效观测、47 个缺失/丢失观测；有效数量直方图为 0:12,1:6,2:8,3:18,4:16。a8d940 60 帧、0–5.9 s、1666 个候选观测、6 个正式段、201 个有效观测、23 个缺失/丢失观测；直方图为 0:3,1:1,2:4,3:16,4:36。候选/段数均不是物理鱼总数。
- 分别独立复核输入与配置 SHA-256、清单快照、60 个连续帧号、严格递增的解码器时间、CSV 候选/组件/观测计数、同帧同编号唯一、每帧有效观测不超过四个；有效坐标在对应原尺度 ROI 内，缺失点 XY 全 NaN 且面积为零，experimental/px/processed_full_frame 来源和单位一致。
- 两次运行都未使用标定、未进行跨视角匹配或重建，物理身份/准确率验证标记均为 false。360 张逐帧 PNG 全部解码且尺寸正确，掩膜值均为 0/255；二维轨迹 PNG 可读，模型 NPZ 可打开且数值数组有限。六张抽样原图及八张复核 JPEG 共十四张均可解码、尺寸符合原视频。
- 此前十七份 YAML 的 SHA-256 与本轮开工快照完全一致；四份改前共享文件备份哈希一致，追加前日志字节不变。新输出校验证据位于 outputs/new_four_video_20261015/output_checks.json；每次独立 run_manifest.json 保存配置快照与哈希。
- git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check 通过，保留原文件 CRLF；git ls-files -ci --exclude-standard 无输出。git check-ignore 确认两段原视频及所有派生结果受 data/ 与 outputs/ 规则保护。
- 主记忆工具受 approval=never 拒绝，恰一次 memorix resume --fallback --brief-json 又被本机 PowerShell 执行策略阻止；已告知用户，以当前仓库及实际运行证据为准，未声称记忆写入成功。

### Notes

- configs/a3d72_raw_multi_confirmed.yaml：新增高分辨率四鱼实体预览配置，实体 ROI (210,40,1020,1560)、镜像 ROI (1390,150,1030,1450)、分割尺寸 102×156，门限继承已有高分辨率配置并注明未用人工标签调优。
- configs/a8d940_multi_confirmed.yaml：新增 960×800 四鱼实体预览配置，实体 ROI (90,20,390,610)、镜像 ROI (550,70,370,540)、分割尺寸 98×152，门限继承已有对应分辨率配置。
- docs/new_four_video_preview.md：新增文件映射、参数来源、可复现命令、实际运行/目视结果、研究限制与新增圈图说明。
- README.md：增加两段新视频的配置及文档入口，保留最初五条和后续四条的事实。
- docs/video_feedback.md：更新新增两段接入状态，将本轮优先复核对象指向新增第 59 帧 raw 图及对应预测图，说明不能强行圈满四条。
- progress.md：仅追加本轮工作和实际验证，保留此前所有历史记录。
- outputs/new_four_video_20261015/video_review/：新增两段报告元信息及首/中/后抽样原尺寸 JPEG，Git 忽略。
- outputs/new_four_video_20261015/a3d72_raw_confirmed/、a8d940_confirmed/：新增两次 60 帧的完整运行产物，Git 忽略，不覆盖旧输出。
- outputs/new_four_video_20261015/manual_review/：新增两段各第 30/59 帧 raw/overlay 原尺寸复核图，Git 忽略，尚无人工坐标或身份标签。
- outputs/new_four_video_20261015/output_checks.json、config_hashes_before.json：新增本轮运行校验结果与既有配置哈希快照，Git 忽略。
- outputs/new_four_video_20261015/rollback_before/：保存四份改前共享文件及哈希，其中 docs/multi_fish_tracking.md 本轮未改，其余三份用于精确恢复。
- 下一最小反馈为两段各第 59 帧中可见实体鱼/反射的圈图，另存 data/annotations/，遮挡或不确定时直接注明；不把算法预测伪造为人工标签。无鱼背景仍未确认，不使用供氧短片冒充空缸，完整三维/行为及整段验证不属于本轮已完成内容。
- 精确回滚（仓库根目录 PowerShell）：`$newFourRollbackRoot = (Resolve-Path '.\outputs\new_four_video_20261015\rollback_before').Path; @('README.md','docs/video_feedback.md','progress.md') | ForEach-Object { Copy-Item -LiteralPath (Join-Path $newFourRollbackRoot $_) -Destination $_ -Force }; Remove-Item -LiteralPath 'configs/a3d72_raw_multi_confirmed.yaml','configs/a8d940_multi_confirmed.yaml','docs/new_four_video_preview.md'`。仅恢复本轮三份共享文件并删除三份本轮新建正式文件，保留 ignored 运行证据及此前未提交工作；没有递归删除、没有提交或推送。
