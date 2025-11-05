<div align="center">
    <h1 align="center">FiF 口语自动化工具</h1>
    <p align="center">TTS自动化完成FiF口语</p>
</div>

# 目录

- 简介
- 快速准备（依赖与环境）
- 启动程序
- GUI 概览
  - 登录配置
  - 跳过设置
  - 等级类型规则
  - 控制区域与运行日志
- 单元测试功能
  - 如何运行测试
  - 测试文件说明
- 配置文件说明（`config.json`）
- 打包为 EXE 文件（Windows）
  - 步骤一：安装 PyInstaller
  - 步骤二：打包命令（推荐参数）
  - 步骤三：体积优化建议
  - 步骤四：运行与分发
  - 其它说明
- 规则示例与使用场景
- 常见问题与故障排查
- 声明
  - 借鉴
  - 引用
- 注意事项

---

## 简介

该工具自动化驱动 FiF 在线口语训练页面：
- 使用浏览器自动化（Playwright）登录并打开 FiF 页面；
- 根据任务与单元逐个进入题目；
- 根据题型（跟读/对话）选择合成并通过虚拟麦克风播放预设答案以完成录音；
- 支持在 GUI 中配置“跳过规则”和“等级类型规则（Role-play / Read）”，并保存到 `config.json`。

> 注：语音合成使用 TTS（由 `tts` 目录中的 `TTSSolver` 封装）。播放在 Windows 上使用 `pyaudio`，在 Linux 使用 `ffmpeg` + pulse 的 pipe-source（需系统支持）。

## 快速准备（依赖与环境）

1. Python：建议使用 3.11（请按你的环境调整）。
2. 创建虚拟环境:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
```

3. 安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

4. Playwright游览器二进制安装（必须运行一次）

```powershell
python -m playwright install
```

5. PyTorch（>=2.0.0） 安装（按是否使用 GPU）
	- 如果你想用 GPU（以 CUDA 11.8 为例）：

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

- 若使用 CUDA 12.1：

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

- 如果不使用 GPU（CPU-only）：

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

（或者直接使用 pip install torch --index-url ...，依据 PyTorch 官方安装页选择最合适命令）

6. pyaudio :
- Windows 上常见安装建议:
Windows 上 pip install pyaudio 容易失败（需要编译 C 扩展）。常用替代：

```powershell
python -m pip install pipwin
python -m pipwin install pyaudio
```

或者下载对应 Python 版本的 [wheel](https://github.com/cgohlke/win_arm64-wheels) 手动安装。

- 如果使用 Linux，请确保系统安装 
	- ffmpeg：用于音频转流
	- pulseaudio（或 pipewire/pactl）：如果"module-pipe-source"，确保 pulseaudio 可用并允许加载模块
安装示例（Debian/Ubuntu）：

```powershell
sudo apt update
sudo apt install -y ffmpeg pulseaudio pavucontrol
```

7. TTS 模型：本项目使用 `TTS` 包（Coqui/TTS 或类似）。第一次合成时会下载模型（可能很大）。请保证网络与磁盘空间充足。

8. 目标音色文件：程序需要一个目标音色的 WAV 文件（例如：`draft/target_voice.wav`）。在 GUI 中可选择并保存路径。

## 启动程序

在项目根目录运行：

```powershell
python src\main.py
```

程序会弹出 GUI。首次运行会创建 `tmp/` 与 `draft/` 目录，并在合成时将临时 WAV 写入 `tmp/`。

## GUI 概览

程序主界面由多个标签页组成，默认打开为“登录配置”。下面逐项说明。

### 登录配置

字段说明：
- 用户名：用于登录 FiF 系统的账号。
- 密码：对应账号密码。
- 目标音色文件：选择一个用于 TTS 的目标音色 WAV（填写完整路径或使用“浏览”按钮）。
- 跳过分数：当某等级的 `levelScore` >= 该值时会跳过该等级，避免重复做高分已通过的题目。

操作流程：
1. 在用户名/密码处填写 FiF 站点的账号密码。
2. 在目标音色文件处点击浏览选择 WAV 文件（或事先把 `draft/target_voice.wav` 放好）。
3. 设置跳过分数（0-100）。
4. 点击“保存配置”以写入 `config.json`。

> 备注：目标音色控件已移到“登录配置”页（位于密码下面，跳过分数上面），保存后会在下一次运行时被使用。

### 跳过设置（Skip Rules）

用途：按单元名/章节类型/章节编号定义跳过规则。每项规则包含：
- 单元匹配文本（`unit_pattern`）: 会以子串匹配方式判断；
- 章类型（`chapter_type`）: 可选 `Any`（跳过整个单元）、`Role-play`、`Expressions`、`Group discussion` 等；
- 章编号（可选，`chapter_num`）: 若填写，会在匹配到等级名时尝试匹配数字或字符串。

示例：
- 匹配 `Unit 1` 整个单元：`unit_pattern` = `Unit 1`，`chapter_type` = `Any`。
- 匹配 `Unit 2` 中编号为 3 的 Role-play：`unit_pattern` = `Unit 2`，`chapter_type` = `Role-play`，`chapter_num` = `3`。

### 等级类型规则（Level Type Rules）

用途：用于显式指定某些单元/等级是“对话（Role-play）”还是“跟读（Read）”。这解决 FiF 页面结构导致的自动判断不准确问题。每条规则包含：
- 单元匹配文本（可空）：按子串匹配单元名。
- 等级匹配文本（可空）：按子串匹配等级名。
- 类型：`Role-play` 或 `Read`。

规则生效行为：当运行时遍历等级，工具会把匹配到 `Role-play` 的等级在传给内部答题解析器前，向 `level_name` 尾部添加一个 ` role` 标记（例如：`Level 1 role`），以触发展示版 `FiFWebClient.get_level_answer` 中对 `role` 的检测，从而把该等级按照对话处理；否则按跟读处理。

示例：
- 让 `Unit 1` 内所有名中包含 `Role-play` 的等级被当作对话：`unit_pattern = Unit 1`, `level_pattern = Role-play`, `type = Role-play`。
- 全局将名字包含 `Expressions` 的等级视为跟读：`unit_pattern = `（留空），`level_pattern = Expressions`, `type = Read`。

> 说明：当前实现使用尾部标记 `role` 的方式作为兼容性方案。如果需要更稳健的实现（显式传递类型参数给 `FiFWebClient`），可考虑改动 `src/connector/FiFWebClient.py`，将 `start_level_test` 和 `get_level_answer` 接口改为接受 `is_roleplay` 布尔值。

### 控制区域与运行日志

- 开始运行 / 停止运行：控制主流程的启动与停止。
- 保存配置：保存当前填写的用户名、密码、跳过分数、目标音色路径、跳过规则与等级类型规则到 `config.json`。
- 运行日志：位于主界面下方，默认高度增大以便查看更多日志信息。运行时会输出登录、加载答案、播放语音、异常信息等。

## 单元测试功能

本项目已集成基础单元测试，测试文件位于 `tests/` 目录。

### 如何运行测试

1. 首次需安装 pytest：
	```powershell
	python -m pip install pytest
	```
2. 在项目根目录运行所有测试：
	```powershell
	pytest
	```
3. 你可以单独运行某个测试文件，例如：
	```powershell
	pytest tests/test_tts.py
	```

### 测试内容说明

- `test_tts.py`：测试 TTS 合成接口，验证能否生成音频数据并写入 `tmp/test_tts.wav`。
- `test_speaker.py`：测试 Speaker 封装的合成与播放接口（如遇声卡或依赖问题会自动跳过）。
- `test_fifwebclient.py`：测试 FiFWebClient 的部分接口（如规则判断、API方法是否可调用）。

如需扩展测试，可在 `tests/` 目录下新建更多 `test_xxx.py` 文件，推荐使用 pytest 风格。

## 配置文件说明（`config.json`）

程序会在保存时把部分设置写入 `config.json`，主要字段示例：

```json
{
  "username": "your_user",
  "password": "your_password",
  "skip_score": 80,
  "target_voice_path": "draft/target_voice.wav",
  "skip_rules": [
	 {"unit_pattern": "Unit 1", "chapter_type": "Any", "chapter_num": ""}
  ],
  "level_type_rules": [
	 {"unit_pattern": "Unit 1", "level_pattern": "Role-play", "level_type": "Role-play"}
  ]
}
```

- `skip_rules` 是跳过规则的数组；
- `level_type_rules` 是等级类型规则（用于将某些等级强制识别为对话或跟读）。

手动编辑 `config.json` 时请保持 JSON 格式正确，并在保存后在 GUI 中点击“刷新”或重启以加载。

## 打包为 EXE 文件（Windows）

本项目可通过 PyInstaller 打包为单个 exe 文件，适用于 Windows 平台。

### 步骤一：安装 PyInstaller

建议使用 5.13.0 及以上版本（兼容 Python 3.10+）：
```powershell
python -m pip install pyinstaller
```

### 步骤二：打包命令（推荐参数）

在项目根目录下运行：
```powershell
pyinstaller src\main.py --onefile --noconsole --name fif_gui --add-data "config.json;." --add-data "draft;draft" --add-data "tmp;tmp" --exclude-module test --exclude-module tests --exclude-module pip --exclude-module setuptools --exclude-module wheel
```
参数说明：
- `--onefile`：生成单个 exe 文件（体积最小化，便于分发）
- `--noconsole`：不弹出命令行窗口（GUI 程序推荐）
- `--name fif_gui`：生成的 exe 文件名
- `--add-data`：打包所需的配置、音色、临时目录（可按需调整）
- `--exclude-module`：排除无用模块（如测试、pip、setuptools、wheel 等）

### 步骤三：体积优化建议

- 只打包必须的依赖和资源，尽量排除测试、开发工具、未用到的第三方包。
- 若 TTS 模型文件较大，可在首次运行时下载，不随 exe 一起分发。
- 可用 UPX 压缩 exe（需安装 upx，PyInstaller 自动检测）：
	- 下载并安装 upx：https://upx.github.io/
	- 打包时自动压缩（PyInstaller 会检测 upx 并使用）。
- 删除 exe 旁生成的 build/、dist/ 目录下无用文件，仅保留最终 exe。

### 步骤四：运行与分发

打包完成后，最终 exe 文件在 `dist/` 目录下（如 `dist\fif_gui.exe`）。
可直接双击运行，无需 Python 环境。
如需分发，请确保 `config.json`、`draft/`、`tmp/` 等必要资源一并提供。

### 其它说明

- Playwright 浏览器二进制（chromium）不随 exe 打包，首次运行需在目标机器上执行：
	```powershell
	python -m playwright install
	```
	或在打包前将浏览器二进制复制到 exe 所在目录。
- 若遇到 DLL 缺失、依赖找不到等问题，可参考 PyInstaller 官方文档或在 spec 文件中手动调整 hiddenimports。

如需进一步缩小体积，可考虑：
- 用 nuitka 替代 PyInstaller（更激进的优化，但兼容性需测试）；
- 用 UPX 进一步压缩；
- 精简 requirements.txt，仅保留实际用到的库。

如需自动生成打包脚本或 spec 文件，请告知你的 Python 版本和目标平台（如 Win10/Win11 x64）。

## 规则示例与使用场景

场景 1（按单元全部跳过）:
- 想跳过 `Unit 3` 的所有等级：在跳过规则中添加 `unit_pattern=Unit 3`, `chapter_type=Any`。

场景 2（仅跳过某类型）:
- 想跳过 `Unit 2` 的 `Expressions` 第 1 章：`unit_pattern=Unit 2`, `chapter_type=Expressions`, `chapter_num=1`。

场景 3（将某等级强制为对话）:
- FiF 页面未明确标注 role-play，但你知道 `Unit 5 Level 2` 是 Role-play：添加等级类型规则 `unit_pattern=Unit 5`, `level_pattern=Level 2`, `level_type=Role-play`。

## 常见问题与故障排查

1. 程序无法登录 / 登录后没有任务：
	- 检查用户名/密码是否正确；
	- 在浏览器弹出窗口中确认页面已成功跳转并授权；
	- 检查网络与站点是否可访问。

2. TTS 无法合成或启动慢：
	- 第一次加载模型会下载并占用时间与磁盘；
	- 检查 `requirements.txt` 中是否安装了 `TTS`、`num2words` 等依赖；
	- 在内存或显存不足时考虑将合成模式改为 CPU（GUI 中初始化参数为 `cpu` 或 `cuda`）。

3. Windows 上声卡播放失败（`pyaudio` 问题）：
	- 确认已正确安装 `pyaudio`；
	- 如果无法通过 `pip` 安装，请尝试 `pipwin` 或从第三方 wheel 安装。

4. Linux 下虚拟麦克风未创建：
	- 确保 `pulseaudio` 正在运行，并允许加载 `module-pipe-source`；
	- 检查 `/tmp/<VirtualPipeMic>` 文件是否存在。

5. 跟读/对话识别不准确：
	- 使用“等级类型规则”显式指定；
	- 如果你愿意，可以把规则改为更严格的匹配（在 GUI 中填写更具体的 `level_pattern`）。

## 声明

### 借鉴

- [Aurorabili/fuckfif](https://github.com/Aurorabili/fuckfif)

### 引用

- [microsoft/playwright](https://github.com/microsoft/playwright)
- [Edresson/YourTTS](https://github.com/Edresson/YourTTS)
- [coqui-ai/TTS](https://github.com/coqui-ai/TTS)

## 注意事项

- 本程序仅用于学习，请勿用于非法用途。
- 仅适用于 FiF 官网的页面，其他站点请自行修改代码。
- 本项目由 Python 3.11 开发，请使用 Python 3.11 或更高版本运行，低于 python 3.11 的用户请自行修改代码。
- Windows 系统用户请下载虚拟麦克风模块，并配置为默认输入源。
- 若末设置等级类型规则，则等级名“Role-play”将默认为“对话”，非等级名“Role-play”将默认为“跟读”。
- 默认使用 GPU 模式，请自行配置 GPU 环境。