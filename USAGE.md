# Concrete Section Analysis — 使用说明与实现方法

本仓库 `concrete_section_analysis` 提供用于不规则对称与矩形钢筋混凝土截面全过程（moment-curvature）分析的工具、GUI、JSON 配置处理器和若干测试/示例数据。

本文档旨在详细说明程序结构、所使用的方法、输入输出格式、如何运行（GUI 与 CLI）、以及调试与扩展建议，便于用户和开发者快速上手与二次开发。

---

## 目录结构（关键文件）

- `analyzer_ver1.py` — 截面分析核心实现（RCSectionAnalyzer）：材料模型、应力—应变关系、截面离散与力平衡求解、极限弯矩/曲率求解。核心算法基于数值积分与迭代求解（见下文方法描述）。
- `material.py` — 材料参数与常量（混凝土等级、钢筋等级、设计值转换等）。
- `json_file_handler.py` — JSON 配置加载/验证/预处理/保存：对用户上传的 JSON 进行结构验证、参数计算（例如材料计算值、钢筋面积）、合理性检查并保存处理后的配置。
- `json_tool.py` — 命令行工具，用于测试/演示 JSON 处理流程（封装了 `FileUploadProcessor`）。
- `irregular_section.py` — 对于不规则对称截面的上层封装：将 JSON 配置转换为分析器可用输入并调用 `RCSectionAnalyzer` 进行计算与结果整理。
- `gui_irregular.py` — 基于 PyQt5 的图形化界面：材料与截面参数输入、JSON 文件选择、分析任务异步执行、结果绘图与摘要展示。
- `main_irregular.py` — （可选）脚本化入口，调用 GUI 或命令行接口（如存在）。
- `input/`、`uploads/`、`processed/`、`results/` — 示例 JSON、上传缓存、处理后文件与历史结果。

---

## 核心方法与实现要点

以下将按功能模块概述实现方法与关键算法思想。

### 1) 材料模型（`material.py` 与 `analyzer_ver1.py` 中的材料子模块）
- 混凝土：采用分段的应力-应变关系（设计值 f_cd、弹性模量 E_c、极限压应变 eps_u 等），并支持抗拉强度简化处理以计算受拉区行为。
- 钢筋：采用弹塑性模型（弹性模量 E_s、屈服强度 f_yd），必要时考虑屈服后塑性段。材料参数通过 `analyzer.set_materials(concrete_type, steel_type)` 初始化。

注意事项与边界条件：代码中在材料参数为 None 时有防护（在 GUI 展示中会显示 `N/A`），防止在尚未初始化材料前执行数值运算。

### 2) 截面离散与几何处理（`analyzer_ver1.py`）
- 矩形截面：直接通过宽高与上下钢筋面积/位置建立截面模型。
- 不规则对称截面：通过 JSON 中的 `contour_points`（一系列 y 与 half_width）描述对称轮廓。实现上先将轮廓沿高度方向离散化（基于传入的曲率/步数），用于数值积分求截面力—应变分布与内力平衡。

常见检查：轮廓 Y 范围是否覆盖 [0, height]，half_width 是否为正，预处理会对不合理数据记录 WARNING 或抛错。

### 3) 平衡方程求解（Moment-Curvature 分析，`analyzer_ver1.py`）
- 输入：材料参数、截面几何、钢筋分布、目标轴力（N）与曲率扫描范围（start, end, steps）。
- 对每一给定曲率 κ，假定平面截面假设，计算混凝土与钢筋对应的应变分布，进而求出应力分布并积分得到轴力与弯矩。随后通过迭代（例如牛顿或弦方法）微调中和轴位置以满足给定轴力（若 N_target ≠ 0）。
- 输出：对于所选 κ 序列，返回 moments、kappas、epsilons0（中和轴应变）、max/min concrete strain、failure_mode、以及极限弯矩等摘要数据。

稳定性与数值健壮性措施：
- 曲率扫描步数 `n_steps` 可调（默认 200——可在 JSON/GUI 中设置），用于控制精度与计算量；过粗可能导致极大误差，过细会花费更多时间。
- 对异常应变/应力值（例如 NaN、无限）加入检测并抛出友好错误，CLI/GUI 层会捕获并显示。

### 4) JSON 处理与验证（`json_file_handler.py`）
- `JSONFileHandler.validate_json_structure(data)`：验证顶层字段（materials, geometry, reinforcement, analysis）及其子字段完整性与合法性（混凝土/钢筋等级是否支持、contour_points 最少 2 个、layers 含 top/middle/bottom 等）。
- `load_json_file(file_path)`：检查存在性、扩展名、大小限制（10MB），解析 JSON 并调用结构验证，返回 `(success, data, message)`。
- `preprocess_config_data(data)`：在完整性验证后，调用 `RCSectionAnalyzer.set_materials` 计算派生材料参数（f_cd, E_c 等），并计算各钢筋层的有效面积（用于后续分析或摘要）。
- `save_processed_config(data, output_path)`：将处理后 JSON 写入 `processed/`（供审计或 GUI 加载使用）。

### 5) GUI（`gui_irregular.py`）
- 前端框架：PyQt5。界面包含材料选择、截面类型（矩形 / 不规则）、参数输入、JSON 文件选择（仅不规则时启用）以及分析参数（目标轴力、步数）与“开始分析”按钮。
- 异步执行：分析在 `AnalysisThread(QThread)` 中运行，避免阻塞主线程。如果发生异常，线程会通过 `analysis_done` 信号发送包含 `error` 键的结果字典回主线程以弹窗提示用户。
- 结果展示：使用 matplotlib（FigureCanvasQTAgg）在 GUI 中绘制 Moment–Curvature 曲线、应变发展与中和轴曲线，并显示结果摘要。

实现注意点：
- 当选择不规则截面时，控件 `config_file_edit` 和 `浏览...` 按钮会被启用以便选择 JSON；在切回矩形时这些控件被禁用以避免误操作。
- GUI 层对从 JSON 加载或分析返回的错误做了统一处理并弹窗提示（`QMessageBox.critical`）。

---

## JSON 配置格式（示例与字段说明）

顶层字段（必需）：
- `section_name` (string, 可选)：截面名称
- `description` (string, 可选)
- `version` (string)
- `materials`: { `concrete_type`: str, `steel_type`: str }
- `geometry`: { `height`: number (mm), `contour_points`: [ {"y": number, "half_width": number}, ... ] }
- `reinforcement`: { `cover_thickness`: number, `layers`: { `top`/`middle`/`bottom`: {`count`: int, `diameter`: number} } }
- `analysis`: { `target_axial_force`: number (kN), `curvature_range`: {`start`, `end`, `steps`} }

注意：`contour_points` 中的 `y` 应从 0 到 `height`，`half_width` 应为正值。`layers` 中即使某层没有钢筋也应提供（例如 count: 0, diameter: 0）。

示例文件：`input/custom_irregular_config.json`、`sample_irregular_stability.json`（仓库中已有）。

---

## 运行方式

1. 依赖（建议使用虚拟环境）

   - Python 3.10+（仓库在 macOS + conda/Miniconda 下测试通过）
   - 主要依赖：PyQt5、matplotlib、numpy（这些在 `analyzer_ver1.py` 中被使用）。

2. 使用命令行测试 JSON 处理（非 GUI）：

```bash
# 在仓库根目录运行
python concrete_section_analysis/json_tool.py concrete_section_analysis/sample_irregular_stability.json --summary
```

CLI 会输出处理结果并把处理后的文件写到 `concrete_section_analysis/processed/`。

3. 启动 GUI：

```bash
# 直接运行 GUI 脚本（视项目入口而定）
python concrete_section_analysis/gui_irregular.py
```

在 GUI 中：
- 选择材料与截面类型；若选择“不规则对称截面”，请使用 `浏览...` 选择 JSON 文件（或在 `input/` 下编辑/放入样例）。
- 点击“开始分析”，等待线程运行完成并查看绘图与摘要。

---

## 测试

- 已添加 pytest 测试 `concrete_section_analysis/tests/test_file_upload_processor.py`（若存在），用于端到端验证 `FileUploadProcessor.process_uploaded_file()`。
- 可运行：

```bash
cd <project_root>
python -m pytest concrete_section_analysis/tests/test_file_upload_processor.py -q
```

建议为以下场景补充单元测试：
- 缺失必需字段的 JSON（断言验证失败并返回合适错误信息）。
- 非 JSON 或损坏 JSON 文件（断言解析错误）。
- 超大文件（超过 10MB）的拒绝逻辑。

---

## 常见问题与故障排查

- GUI 看不到 `浏览...` 按钮或无法点击：切换到“不规则对称截面”，控件会被启用；若仍不可用，检查是否有本地回退修改导致 `setEnabled`/`setVisible` 的行为被修改。
- JSON 验证报错：使用 `json_tool.py` 可快速得到验证错误信息；检查 `materials`、`geometry.contour_points`、`reinforcement.layers` 等必需字段。
- 处理后文件未生成：确认 `processed/` 目录是否可写；检查日志（`json_file_handler` 使用 logging，默认 INFO 级别）。
- GUI 分析过程中界面无响应：分析逻辑在 `QThread` 中执行，若发现阻塞，检查是否在主线程中调用了长耗时函数或在信号回调中做了大量计算。

---

## 扩展与改进建议

- 支持更多的材料模型/粘结滑移模型，以提高对复杂钢筋行为的模拟精度。
- 将分析器核心包装为一个 REST/HTTP 服务以便远程批量提交 JSON 并异步返回结果。
- 在 GUI 中加入进度条（当前仅显示“分析中...”），可以在 `AnalysisThread` 中周期性发射进度信号。
- 为不规则截面增加自动网格细化选项：根据截面几何在关键区域增加积分点以提高精度。

---

## 开发者提示

- 代码风格：保持模块化，分析器（numerical core）应尽量与 I/O（JSON/GUI）分离；方便单元测试。
- 在修改 `analyzer_ver1.py` 时，优先添加单元测试来覆盖数值稳定性（不同曲率步长、不同轴力），以避免引入回归。

---

如果你希望我把这份文档转换为仓库根下的 `README.md`，或把部分内容写入 `GUI_JSON_UPLOAD_README.md`（更聚焦 GUI 的使用），我可以继续追加修改。另外，我可以基于此生成一个快速入门脚本或 CI 测试配置（GitHub Actions）来在每次提交时运行关键单元测试。

最后更新：见仓库 `concrete_section_analysis` 下的 `USAGE.md`。