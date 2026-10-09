# S2 视频读取与预处理

输入为配置文件和视频；`video-demo` 先生成带 `SYNTHETIC` 字样的合成 AVI。
该视频的尺寸、帧率、帧数、两块 ROI、鱼形状及颜色均来自
`configs/synthetic_video.yaml`，不是论文装置参数，也不是实验录像。

每帧按如下顺序处理：读取 BGR 和时间戳 → 可选相机去畸变 → 中值滤波 →
OpenCV HSV 转换 → 按配置裁剪 `mirror`、`real` ROI。ROI 在校正后的全帧
坐标系中定义，矩形采用左上角 `(x,y)`、宽、高，右与下边界不包含。
`ViewFrame` 保留 ROI 原点，供后续质心结果换算为全帧像素坐标。
两块 ROI 必须在图像内且不重叠；实际边界需由实验画面确认。

去畸变配置 `preprocessing.calibration_file` 可指向 UTF-8 JSON 文件；
相对路径以 YAML 所在目录为基准。JSON 字段为 `camera_matrix`（3×3）、
`distortion_coefficients`（4、5、8、12 或 14 个值）、`image_width`、
`image_height`。未配置时保留原图，并在运行记录写入
`calibration_applied=false`；这不代表图像已经校正。真实标定文件若为
MATLAB `.mat` 或 OpenCV XML，需在后续真实视频接入时先转换并核验。

输出目录包含 `undistorted_bgr/`、`median_bgr/` PNG，`full_hsv/`、
`mirror_hsv/`、`real_hsv/` 的 `.npy` 原始数组，以及供人工查看的
`mirror_preview/`、`real_preview/` PNG。HSV 使用 OpenCV uint8 范围：
H=0..179，S/V=0..255；不要把 `.npy` 直接当 RGB 图打开。
`frames.csv` 保存帧号、时间戳、来源、时间戳来源及 ROI 原点；
`run_manifest.json` 保存输入视频和配置的 SHA-256、配置快照、帧数及
是否应用标定。

优先采用解码器返回的 `CAP_PROP_POS_MSEC`；当其缺失或不递增时，
按视频报告帧率（否则按配置的 `fps_fallback`）递推时间，并逐帧标记
`timestamp_source=fps_fallback`。OpenCV 时间戳不能保证还原可变帧率视频的
原始逐帧时间；正式实验若有独立时间戳，应提供对应表并另行校验。

S2 不执行背景建模、目标检测或三维重建。真实视频接入还需实验人员提供：
保持实体鱼和镜像同帧的原始视频、分辨率及录制帧率或逐帧时间戳、
可读取的相机内参和畸变参数、ROI 参考画面、镜面及鱼缸几何记录。

