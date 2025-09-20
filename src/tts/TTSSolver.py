import os
from TTS.api import TTS  

class TTSSolver:
    def __init__(self, model, mode, target_voice_path):
        print("[TTS] 正在初始化神经网络。")
        self.model = model
        self.target_voice_path = target_voice_path
        self.tts = TTS("tts_models/multilingual/multi-dataset/your_tts", 
                       gpu=True if mode == "cuda" else False, 
                       progress_bar=True)
    
    def get_voice(self, text):
        return

    def get_file(self, text: str, path):
        if text == "":
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        print("[TTS] 正在合成语音。")
        # 解决单词过少导致的bug
        # 当句子中只有1个单词时，在句子前加上"Oh, "以增加单词数
        if len(text.split(" ")) <= 1:
            text =  "Oh, " + text
            
        self.tts.tts_to_file(
            text=text,
            speaker_wav=self.target_voice_path,
            language="en",
            file_path=path,
        )
        return