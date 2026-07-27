<div align="center">
    <h1 align="center">FiF Speaking Automation Tool</h1>
    <p align="center">Automate FiF speaking tasks using TTS</p>
</div>

- This project automates FiF speaking tasks via TTS. It provides a cross-platform graphical interface, eliminating the need for manual browser operation and recording. **For educational and personal use only; please do not use for illegal purposes.**

---

# Project Introduction

- Implements automatic batch completion of FiF speaking training tasks using browser automation (Playwright) and GUI management.
- Supports multiple question types (Read-along/Dialogue) and allows custom skip and type recognition rules for specific units/levels.
- Generates speech via TTS and automatically submits answers through a virtual microphone.

---

# Environment Requirements

- **Operating System:**
  - Windows 11 recommended (Linux is theoretically supported and requires pulseaudio, but **has not been deployed/tested**).
- **Python Version:**  
  - **Python 3.11 or higher is required**; the latest version is recommended.
- **Recommended Hardware:**  
  - GPU available (faster); CPU mode is available if no GPU is present (slower).

---

# Installation and Configuration

## 1. Clone Repository and Install Python Dependencies

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

## 2. Install PyTorch

Please choose based on whether you have a GPU and your corresponding CUDA version (select the CPU version if no GPU is available).

- **With NVIDIA GPU (CUDA 11.8 recommended):**
  ```sh
  pip install torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu118
  ```
- **Without GPU (CPU execution):**
  ```sh
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```

*For more CUDA versions, please refer to the [PyTorch official website](https://pytorch.org/get-started/previous-versions/).*

## 3. Install Playwright Browser Drivers

Run the following after the first installation:

```sh
python -m playwright install
```

## 4. Install Audio Playback Dependencies (Optional)

- **Windows**:  
  If installing the `pyaudio` library from `requirements.txt` in the first step fails, you can install `pyaudio` manually using `pipwin`:
  ```sh
  pip install pipwin
  pipwin install pyaudio
  ```
  If that fails, you can download the wheel file for offline installation [here](https://github.com/cgohlke/win_arm64-wheels).

- **Linux** (requires ffmpeg + pulseaudio; please configure manually if you do not have root permissions):
  ```sh
  sudo apt update
  sudo apt install -y ffmpeg pulseaudio pavucontrol
  ```

## 5. Other Dependency Notes

- TTS models will be downloaded automatically during the first speech synthesis; a stable network environment and sufficient disk space are required.
- Prepare a target timbre `.wav` audio file (e.g., `draft/target_voice.wav`) to be used for synthesis.

---

# Quick Start

1. Configure the dependencies mentioned above and start the service.
2. Run:

```sh
python src/main.py
```

3. The first run will automatically create `tmp/` and `draft/` directories. You can configure accounts, target timbres, rules, etc., within the GUI.
4. Configuration information is saved in `config.json`. It is recommended to click the "Save Configuration" button after every change.

---

# Common Issues (FAQ)

- **Virtual Microphone Errors**
  - Linux: Requires pulseaudio support. If initialization fails, please manually check if the `/tmp/<VirtualPipeMic>` file exists, or manually execute the `pactl` commands as indicated in the output.
  - Windows: If `pyaudio` reports an error, please confirm it was installed via `pipwin` and try again after restarting.

- **Model Download Timeout or Missing Files**
  - You can manually download the [YourTTS model](https://coqui.gateway.scarf.sh/v0.10.1_models/tts_models--multilingual--multi-dataset--your_tts.zip) as prompted and place it in the specified user TTS path (`C:\Users\<User>\AppData\Local\tts`).  
    Note: The `AppData` directory is hidden; you must enable "Show hidden files" to see it. The `tts` folder may need to be created manually.
- **GUI Unresponsive or Abnormal**
  - Check the Python version, dependency packages, and `config.json` format. Delete `config.json` and reconfigure if necessary.

---

# Configuration File Example (`config.json`)

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

# Code Structure

```
src
├── main.py             # Main program
├── connector           # FiF client connector
├── speaker             # Speech synthesizer abstraction
├── tts                 # TTS model
└── vmic                # Virtual microphone
```

---

# TTS Model File Structure

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

# Disclaimer

- For personal learning purposes only.
- The operation of this program and the speech models depends on the environment. The development/runtime environment must meet Python 3.11 and the dependencies listed above; some edge cases have not been deeply optimized for compatibility.

---

# Acknowledgments and Citations

- [microsoft/playwright](https://github.com/microsoft/playwright)
- [coqui-ai/TTS](https://github.com/coqui-ai/TTS)
- [Aurorabili/fuckfif](https://github.com/Aurorabili/fuckfif)
