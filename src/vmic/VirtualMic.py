# 虚拟麦克风/播放封装，跨平台：Linux 使用 pipe-source（外部依赖），Windows 使用 pyaudio
import os
import platform
import wave
from pathlib import Path
from typing import Optional

CHUNK = 1024

try:
    import pyaudio
except Exception:
    pyaudio = None


class VirtualMic:
    def __init__(self, device_name: str, fmt: str, rate: str, channels: str):
        self.device_name = device_name
        self.format = fmt
        self.rate = int(rate)
        self.channels = int(channels)
        self.system = platform.system()

        if self.system == "Linux":
            self._init_linux()
        elif self.system == "Windows":
            self._init_windows()
        else:
            raise Exception(f"Unsupported operating system: {self.system}")

    def _init_linux(self) -> None:
        retry = 0
        while not Path(f"/tmp/{self.device_name}").exists():
            retry += 1
            if retry > 5:
                raise Exception("[VirtualMic] 虚拟声卡初始化失败。请确保 pulseaudio/pactl 可用。")
            print("[VirtualMic] 开始初始化虚拟声卡。")
            os.system(
                "pactl load-module module-pipe-source source_name={} file=/tmp/{} format={} rate={} channels={}".format(
                    self.device_name,
                    self.device_name,
                    self.format,
                    self.rate,
                    self.channels,
                )
            )
            os.system(
                "pacmd update-source-proplist {} device.description={}".format(
                    self.device_name, self.device_name
                )
            )
            os.system("pacmd set-default-source {}".format(self.device_name))
        print("[VirtualMic] 虚拟声卡初始化完成。")

    def _init_windows(self) -> None:
        print("[VirtualMic] Windows 系统，使用 VB-Cable 虚拟声卡")
        if pyaudio is None:
            print("[VirtualMic] 警告: pyaudio 未安装，无法在 Windows 上播放音频。")
            return

        # 查找 VB-Cable 设备（取第一个非 Point 版本）
        self._cable_output_idx = None
        self._cable_input_idx = None
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            name = info["name"]
            if "CABLE Input" in name and info["maxOutputChannels"] > 0:
                print(f"[VirtualMic] 虚拟扬声器: [{i}] {name}")
                if self._cable_output_idx is None:
                    self._cable_output_idx = i
            if "CABLE Output" in name and info["maxInputChannels"] > 0:
                print(f"[VirtualMic] 虚拟麦克风: [{i}] {name}")
                if self._cable_input_idx is None:
                    self._cable_input_idx = i
        p.terminate()

        if self._cable_output_idx is None:
            print("[VirtualMic] 警告: 未找到 VB-Cable，使用默认扬声器")

        # 设置系统默认录音设备为 VB-Cable
        self._set_default_recording_device()

    def _set_default_recording_device(self) -> None:
        """设置系统默认录音设备为 VB-Cable（虚拟麦克风）。"""
        try:
            from pycaw.utils import AudioUtilities

            devices = AudioUtilities.GetAllDevices()
            for dev in devices:
                name = getattr(dev, 'FriendlyName', '') or ''
                if "CABLE Output" in name:
                    AudioUtilities.SetDefaultDevice(dev.id)
                    print(f"[VirtualMic] 默认录音设备已切换为: {name}")
                    return

            print("[VirtualMic] 未找到 CABLE Output 录音设备，保持默认麦克风")
        except Exception as e:
            print(f"[VirtualMic] 切换录音设备失败: {e}")
            print("[VirtualMic] 请手动：右键任务栏喇叭 → 声音设置 → 输入 → 选择「CABLE Output」")

    def play(self, file_path: str) -> None:
        if not Path(file_path).exists():
            print(f"[VirtualMic] 音频文件不存在: {file_path}")
            return

        if self.system == "Linux":
            self._play_linux(file_path)
        elif self.system == "Windows":
            self._play_windows(file_path)

    def _play_linux(self, file_path: str) -> None:
        print(f"[VirtualMic] 音频流开始从 {file_path} 写到虚拟声卡中。")
        os.system(
            "ffmpeg -re -i {} -f {} -ar {} -ac {} -async 1 -filter:a volume=0.8 - > /tmp/{} 2>/dev/null".format(
                file_path, self.format, self.rate, self.channels, self.device_name
            )
        )
        print(f"[VirtualMic] 音频流结束: {file_path}")

    def _play_windows(self, file_path: str) -> None:
        print(f"[VirtualMic] 音频 -> VB-Cable 虚拟声卡: {file_path}")

        if pyaudio is None:
            print("[VirtualMic] 错误: pyaudio 未安装，无法播放。")
            return

        p = None
        stream = None
        try:
            with wave.open(file_path, 'rb') as wf:
                sampwidth = wf.getsampwidth()
                channels = wf.getnchannels()
                orig_rate = wf.getframerate()
                raw_data = wf.readframes(wf.getnframes())

            # 如果采样率不被设备支持，重采样到 44100Hz
            target_rate = orig_rate
            if orig_rate < 22050:
                target_rate = 44100
                print(f"[VirtualMic] 采样率转换: {orig_rate}Hz -> {target_rate}Hz")
                import numpy as np
                # 将原始 PCM 转为 numpy array
                dtype = np.int16 if sampwidth == 2 else np.int32
                audio = np.frombuffer(raw_data, dtype=dtype)
                if channels > 1:
                    audio = audio.reshape(-1, channels)
                # 线性插值重采样
                old_len = audio.shape[0] if channels == 1 else audio.shape[0]
                new_len = int(old_len * target_rate / orig_rate)
                if channels == 1:
                    indices = np.linspace(0, old_len - 1, new_len)
                    audio = np.interp(indices, np.arange(old_len), audio).astype(dtype)
                else:
                    new_audio = np.zeros((new_len, channels), dtype=dtype)
                    for ch in range(channels):
                        indices = np.linspace(0, old_len - 1, new_len)
                        new_audio[:, ch] = np.interp(indices, np.arange(old_len), audio[:, ch]).astype(dtype)
                    audio = new_audio
                raw_data = audio.tobytes()

            p = pyaudio.PyAudio()
            output_kwargs = dict(
                format=p.get_format_from_width(sampwidth),
                channels=channels,
                rate=target_rate,
                output=True,
            )
            # 输出到 VB-Cable 虚拟声卡（不经过实体扬声器）
            if self._cable_output_idx is not None:
                output_kwargs["output_device_index"] = self._cable_output_idx

            stream = p.open(**output_kwargs)

            # 分块写入
            chunk = CHUNK * sampwidth * channels
            pos = 0
            while pos < len(raw_data):
                stream.write(raw_data[pos:pos + chunk])
                pos += chunk

        except Exception as e:
            print(f"[VirtualMic] 播放错误: {e}")

        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            try:
                if p is not None:
                    p.terminate()
            except Exception:
                pass

        print("[VirtualMic] Windows 音频播放完成。")