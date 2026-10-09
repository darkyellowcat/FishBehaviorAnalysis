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
