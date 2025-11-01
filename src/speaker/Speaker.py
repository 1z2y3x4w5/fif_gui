from pathlib import Path
import tempfile
from typing import Optional

from tts.TTSSolver import TTSSolver
from vmic.VirtualMic import VirtualMic


class Speaker:
    """负责调用 TTS 合成并通过虚拟麦克风播放音频的简单封装。"""

    def __init__(self, tts_model_name: str, mode: str, vmic: str, target_voice_path: str):
        self.tts_solver = TTSSolver(tts_model_name, mode, target_voice_path)
        self.virtual_mic = VirtualMic(vmic, "s16le", "44100", "2")

        # ensure tmp exists
        Path("tmp").mkdir(parents=True, exist_ok=True)

    def speak(self, text: str) -> None:
        """合成文本并通过虚拟麦克风播放。"""
        if not text:
            return

        print("[Speaker] 合成语音 -> 播放")

        # 使用临时文件避免竞态并保证唯一
        with tempfile.NamedTemporaryFile(suffix=".wav", dir="tmp", delete=False) as tf:
            temp_path = tf.name

        try:
            # 合成并写入临时文件
            self.tts_solver.get_file(text, temp_path)

            # 播放
            self.virtual_mic.play(temp_path)

        finally:
            try:
                Path(temp_path).unlink()
            except Exception:
                # 忽略删除失败（可能正在被播放）
                pass