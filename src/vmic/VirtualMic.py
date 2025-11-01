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
        print("[VirtualMic] Windows 系统，使用 pyaudio 进行音频输出")
        if pyaudio is None:
            print("[VirtualMic] 警告: pyaudio 未安装，无法在 Windows 上播放音频。")

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
        print(f"[VirtualMic] 在 Windows 上播放音频: {file_path}")

        if pyaudio is None:
            print("[VirtualMic] 错误: pyaudio 未安装，无法播放。")
            return

        p = None
        stream = None
        try:
            with wave.open(file_path, 'rb') as wf:
                p = pyaudio.PyAudio()
                stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True)

                data = wf.readframes(CHUNK)
                while data:
                    stream.write(data)
                    data = wf.readframes(CHUNK)

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