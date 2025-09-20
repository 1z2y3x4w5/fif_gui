# 使用pyaudio库实现Windows兼容的虚拟麦克风
import os
import platform
import pyaudio
import wave

class VirtualMic:
    def __init__(self, device_name, format, rate, channels):
        self.device_name = device_name
        self.format = format
        self.rate = int(rate)
        self.channels = int(channels)
        self.system = platform.system()
        
        if self.system == "Linux":
            self._init_linux()
        elif self.system == "Windows":
            self._init_windows()
        else:
            raise Exception(f"Unsupported operating system: {self.system}")

    def _init_linux(self):
        retry = 0
        while not os.path.exists("/tmp/" + self.device_name):
            retry = retry + 1
            if retry > 5:
                raise Exception("[VirtualMic] 虚拟声卡初始化失败。")
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

    def _init_windows(self):
        print("[VirtualMic] Windows系统，使用pyaudio进行音频输出")
        # 在Windows上，我们将使用pyaudio直接播放到默认输出设备
        # 用户需要确保系统音频设置正确
        
    def play(self, file_path):
        if self.system == "Linux":
            self._play_linux(file_path)
        elif self.system == "Windows":
            self._play_windows(file_path)

    def _play_linux(self, file_path):
        print("[VirtualMic] 音频流开始从{}读到虚拟声卡中。".format(file_path))
        os.system(
            "ffmpeg -re -i {} -f {} -ar {} -ac {} -async 1 -filter:a volume=0.8 - > /tmp/{} 2>/dev/null".format(
                file_path, self.format, self.rate, self.channels, self.device_name
            )
        )
        print("[VirtualMic] 音频流结束。".format(file_path))

    def _play_windows(self, file_path):
        print(f"[VirtualMic] 在Windows上播放音频: {file_path}")
        
        # 打开音频文件
        wf = wave.open(file_path, 'rb')
        
        # 初始化PyAudio
        p = pyaudio.PyAudio()
        
        # 打开流
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
        
        # 读取数据
        data = wf.readframes(1024)
        
        # 播放音频
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        
        # 停止流
        stream.stop_stream()
        stream.close()
        
        # 关闭PyAudio
        p.terminate()
        
        print("[VirtualMic] Windows音频播放完成。")