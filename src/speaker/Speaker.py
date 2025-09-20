import os
from tts.TTSSolver import TTSSolver
from vmic.VirtualMic import VirtualMic

class Speaker:
    def __init__(self, tts_model_name, mode, vmic, target_voice_path):
        self.tts_solver = TTSSolver(tts_model_name, mode, target_voice_path)
        self.virtual_mic = VirtualMic(vmic, "s16le", "44100", "2")
        
        # 确保tmp目录存在
        os.makedirs("tmp", exist_ok=True)
        
    def speak(self, text: str):
        print("[Speaker] 正在合成语音。")
        temp_file_path = "tmp/temp.wav"
        
        # 确保tmp目录存在
        os.makedirs("tmp", exist_ok=True)
        
        self.tts_solver.get_file(text, temp_file_path)
        print("[Speaker] 正在播放语音。")
        self.virtual_mic.play(temp_file_path)
        print("[Speaker] 语音播放完成。")
        return