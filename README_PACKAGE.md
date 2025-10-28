打包为 Windows .exe 说明
=========================

概述
----
本目录包含用于将 `concrete_section_analysis` 打包为 Windows 可执行文件（.exe）的说明和 CI 工作流。推荐使用 PyInstaller 在 Windows 环境中构建。直接在 macOS 上使用 PyInstaller 交叉构建 Windows exe 通常不可行，推荐两种方案：

- 在本地 Windows 机器或虚拟机上构建；
- 使用 GitHub Actions（已提供 workflow），在 Windows runner 上自动构建并上传产物。

快速开始（在本地构建）
--------------------------------

Windows 本地构建
~~~~~~~~~~~~~~~~~
1. 安装 Python（建议 3.11），并创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

2. 在项目根目录运行 PyInstaller（单文件 exe）：

```powershell
pyinstaller --onefile --name concrete_section_analysis \
  --add-data "concrete_section_analysis\input;concrete_section_analysis\input" \
  --add-data "concrete_section_analysis\results;concrete_section_analysis\results" \
  concrete_section_analysis/main_irregular.py
```

构建完成后，生成的 exe 位于 `dist\concrete_section_analysis.exe`。

Unix (Linux/macOS) 本地构建
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. 创建并激活虚拟环境，然后安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

2. 运行 PyInstaller（注意 add-data 在类 Unix 平台使用 ':' 分隔）：

```bash
pyinstaller --onefile \
  --name concrete_section_analysis_unix \
  --add-data "concrete_section_analysis/input:concrete_section_analysis/input" \
  --add-data "concrete_section_analysis/results:concrete_section_analysis/results" \
  concrete_section_analysis/main_irregular.py
```

构建完成后，生成的可执行文件位于 `dist/concrete_section_analysis_unix`（对 macOS，文件通常可直接运行）。

注意事项
---------
- 如果你的脚本依赖本地非 Python 数据文件（如 `input/` 下的 JSON），需要用 `--add-data` 将它们包含进 exe（如上所示）。
- PyInstaller 在不同平台上对于 add-data 的路径分隔符不同：Windows 上使用 `;`，类 Unix 平台使用 `:`。CI workflow 已针对 Windows runner 使用 `;`。
- 若需要 GUI 版本或无控制台，移除或替换 `--onefile` 和加入 `--windowed`。

使用 GitHub Actions 自动构建（跨平台）
--------------------------------
仓库根目录已添加工作流：

- `.github/workflows/build-windows-exe.yml`（单平台 Windows 构建，保留以兼容旧配置）
- `.github/workflows/build-multi-exe.yml`（矩阵构建：Ubuntu / Windows / macOS）

触发方式：push 到 `main`/`master` 分支或手动在 Actions 面板触发（workflow_dispatch）。

工作流会在对应 runner 上安装 Python 与依赖，使用 PyInstaller 构建单文件可执行，并把 `dist/` 下产物上传为 artifacts，用户可在 Actions 运行页面下载对应平台的二进制文件。

跨平台/替代方法
-----------------
- 如果你需要在 macOS 上自动构建 Windows exe，可以在 CI 中使用 Windows runner（推荐）或尝试使用 Docker + Wine，但成功率和兼容性不如直接在 Windows 上构建。
- 要构建 macOS 本地可执行或 app，使用 py2app / pyinstaller 在 macOS 上构建（注意与当前需求不同）。

后续
----
我可以：
- 帮你定制 PyInstaller 的 spec 文件以包含额外资源或调整打包细节；
- 添加一个 GitHub Actions 发布步骤，把 exe 发布到 GitHub Releases；
- 或者为你的主程序制作一个简单的安装脚本/包装器（.bat）以便用户运行。

如需继续，我可以现在为你添加：
- 一个 PyInstaller spec 文件，或
- 在 workflow 中添加自动发布到 Releases 的步骤。
