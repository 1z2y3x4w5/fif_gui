<div align="center">
    <h1>FiF 口语自动化工具</h1>
    <p>TTS 自动化完成 FiF 口语任务 · 虚拟声卡静音运行</p>
</div>

> 本项目通过 TTS + 虚拟声卡自动化完成 FiF 口语训练。提供 Windows 图形界面，静音运行，不受环境噪音影响。
> **仅供学习用途，请勿用于非法用途。**

---

## ✨ 新特性 (v2.0)

- 🔐 **手动登录** — 浏览器打开后手动登录，自动检测并接续执行
- 🎮 **GPU 自动检测** — CUDA 可用时自动启用，RTX 系列秒级合成
- 🔇 **虚拟声卡内录** — 基于 VB-Cable，音频直通浏览器，无需外放
- 📊 **智能跳过规则** — 按单元/等级类型/分数自定义跳过条件
- 🎯 **用户信息自动提取** — 从 localStorage + JWT 解码获取，无需调用已废弃 API

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 |
| Python | 3.11+ |
| GPU | 推荐 NVIDIA（RTX 2060+），CPU 也可运行 |
| 其他 | VB-Audio Virtual Cable（虚拟声卡） |

---

## 快速开始

### 1. 克隆并安装依赖

```powershell
git clone https://github.com/1z2y3x4w5/fif_gui.git
cd fif_gui
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 安装 PyTorch

```powershell
# 有 NVIDIA GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 仅 CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 3. 安装 Playwright 浏览器

```powershell
python -m playwright install
```

### 4. 安装虚拟声卡（推荐）

下载 [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) 安装，实现静音内录。

> 不安装也可用，但会通过扬声器外放，受环境噪音影响。

### 5. 准备参考音频

录一段 5-10 秒英文语音，保存为 `draft/target_voice.wav`（WAV 格式）。

### 6. 运行

```powershell
python src/main.py
```

### 模型下载

首次运行会自动下载 YourTTS 模型（约 400MB）。国内用户建议手动下载后用 aria2 加速：

```powershell
# 安装 aria2
winget install aria2.aria2

# 多线程下载
aria2c -x16 -s16 "https://github.com/coqui-ai/TTS/releases/download/v0.10.1_models/tts_models--multilingual--multi-dataset--your_tts.zip"

# 解压到
# C:\Users\<用户名>\AppData\Local\tts\tts_models--multilingual--multi-dataset--your_tts\
```

---

## 使用指南

| 标签页 | 功能 |
|--------|------|
| 登录配置 | 填写 FiF 账号、选择参考音频、设置跳过分数 |
| 跳过设置 | 按单元/等级类型/编号设置跳过规则 |
| 等级类型规则 | 区分 Role-play（对话）和 Read（跟读） |

1. 填写配置 → 保存配置
2. 点击 **开始运行**
3. 浏览器打开登录页 → **手动登录**
4. 程序自动检测登录成功 → 开始批量答题

---

## 工作流程

```
登录 (手动) → 获取任务列表 → 遍历单元 → 跳过达标项
    → TTS 合成语音 → 虚拟声卡输出 → 浏览器录音 → 自动提交
```

---

## 配置文件

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

## 代码结构

```
src
├── main.py                 # GUI 主程序
├── connector/
│   └── FiFWebClient.py     # Playwright 浏览器自动化
├── speaker/
│   └── Speaker.py          # TTS + 播放封装
├── tts/
│   └── TTSSolver.py        # Coqui YourTTS 引擎
└── vmic/
    └── VirtualMic.py       # VB-Cable 虚拟声卡
```

---

## 常见问题

| 问题 | 解决 |
|------|------|
| 模型下载失败 | 手动下载 aria2c 加速，或从 GitHub Releases 下载后解压 |
| VB-Cable 播放错误 | 确保安装后重启电脑；采样率自动转换已内置 |
| 登录后无法获取用户信息 | 已修复，现从 localStorage + JWT 提取 |
| EPIPE 浏览器崩溃 | 已添加 Chromium 稳定性参数 |
| pyaudio 安装失败 | `pip install pipwin && pipwin install pyaudio` |

---

## TTS 模型文件位置

```
C:\Users\<用户名>\AppData\Local\tts\tts_models--multilingual--multi-dataset--your_tts\
├── config.json
├── config_se.json
├── language_ids.json
├── model_file.pth
├── model_se.pth
└── speakers.json
```

> AppData 为隐藏目录，需开启显示隐藏文件后才能看到。

---

## 致谢

- [microsoft/playwright](https://github.com/microsoft/playwright)
- [coqui-ai/TTS](https://github.com/coqui-ai/TTS)
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
- [Aurorabili/fuckfif](https://github.com/Aurorabili/fuckfif)
