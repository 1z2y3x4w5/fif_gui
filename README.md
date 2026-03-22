<div align="center">
    <h1 align="center">FiF 口语自动化工具</h1>
    <p align="center">TTS自动化完成FiF口语</p>
</div>

- 本项目通过 TTS 自动化完成 FiF 口语任务。提供跨平台图形界面，无需手动操作浏览器及录音。**仅供学习和个人用途，请勿用于非法用途。**

---

# 项目简介

- 使用浏览器自动化（Playwright）与 GUI 管理，实现 FiF 口语训练任务的自动批量完成。
- 支持多种题型（跟读/对话），并可针对单元/等级自定义跳过与类型识别规则。
- TTS 生成语音，通过虚拟麦克风自动提交答案。

---

# 环境要求

- **操作系统：**
  - 推荐 Windows 11（理论支持 Linux，需 pulseaudio，**未部署过**）。
- **Python 版本：**  
  - **必须 Python 3.11 或更高**，建议使用最新版。
- **推荐硬件：**  
  - 有可用 GPU（更快），无 GPU 可用 CPU 模式（速度慢）。

---

# 安装与配置

## 1. 克隆仓库并安装 Python 依赖

```sh
git clone https://github.com/1z2y3x4w5/fif_gui.git
cd fif_gui
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

## 2. 安装 PyTorch

请根据自己是否有 GPU 及对应 CUDA 版本选择（如无 GPU 可选 CPU 版）。

- **有 NVIDIA GPU（推荐 CUDA 11.8）：**
  ```sh
  pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu118
  ```
- **无 GPU（CPU 运行）：**
  ```sh
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```

*更多 CUDA 版本，请参考 [PyTorch 官网](https://pytorch.org/get-started/previous-versions/)。*

## 3. 安装 Playwright 浏览器驱动

首装后需执行：

```sh
python -m playwright install
```

## 4. 安装音频播放依赖（可选）

- **Windows**：  
  如果第一步安装requirement.txt里的pyaudio库有误时，可手动使用 pipwin 安装 pyaudio
  ```sh
  pip install pipwin
  pipwin install pyaudio
  ```
  如果失败也可去 [这里](https://github.com/cgohlke/win_arm64-wheels) 下载 wheel 文件离线安装。

- **Linux**（需 ffmpeg + pulseaudio，如果非 root 权限注意自行配置）:
  ```sh
  sudo apt update
  sudo apt install -y ffmpeg pulseaudio pavucontrol
  ```

## 5. 其它依赖说明

- 首次合成语音会自动下载 TTS 模型，需良好网络环境和充足磁盘空间。
- 准备一个目标音色 wav 音频（如 `draft/target_voice.wav`），用于合成。

---

# 快速开始

1. 配置好上述依赖并启动服务
2. 运行

```sh
python src/main.py
```

3. 首次运行会自动创建 `tmp/` 和 `draft/` 目录，可在 GUI 里实现账号、目标音色、规则等配置。
4. 配置信息会保存在 `config.json`，推荐每次更改后点击“保存配置”按钮。

---

# 常见问题

- **虚拟麦克风相关报错**
  - Linux：需 pulseaudio 支持。若初始化失败，请手动检查 `/tmp/<VirtualPipeMic>` 文件是否存在，或参照输出手动执行 `pactl` 指令。
  - Windows：若 pyaudio 报错请确认已用 pipwin 安装，重启后重试。

- **模型下载超时或缺失**
  - 可手动按提示下载 [YourTTS 模型](https://coqui.gateway.scarf.sh/v0.10.1_models/tts_models--multilingual--multi-dataset--your_tts.zip)，放到用户 TTS 指定路径(C:\Users\ <用户>\AppData\Local\tts)下。  
    注： AppData 目录为隐藏目录，需开启显示隐藏文件后才能看到；
        tts 文件夹可能需要手动创建。
- **GUI 界面无响应或异常**
  - 检查 Python 版本、依赖包和 config 配置格式，必要时删除 `config.json` 重新配置。

---

# 配置文件示例（`config.json`）

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

---

# 代码结构说明
```
src
├── main.py             # 主程序
├── connector           # FiF客户端连接器
├── speaker             # 语音合成器抽象
├── tts                 # TTS模型
└── vmic                # 虚拟麦克风
```

---

# tts 模型文件位置结构说明
```
tts
└── tts_models--multilingual--multi-dataset--your_tts
    ├── config.json
    ├── config_se.json
    ├── language_ids.json
    ├── model.pth
    ├── model_se.pth
    └── speakers.json
```

---

# 免责声明

- 仅供个人学习用途。
- 本程序及语音模型运行情况与环境有关，开发/运行环境需满足 Python 3.11 及上述依赖，部分边界未做深度兼容处理。

---

# 致谢与引用

- [microsoft/playwright](https://github.com/microsoft/playwright)
- [coqui-ai/TTS](https://github.com/coqui-ai/TTS)
- [Aurorabili/fuckfif](https://github.com/Aurorabili/fuckfif)