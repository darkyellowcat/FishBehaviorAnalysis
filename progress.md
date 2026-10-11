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
