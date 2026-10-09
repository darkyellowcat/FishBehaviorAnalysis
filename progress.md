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


