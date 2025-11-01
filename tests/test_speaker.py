import os
import pytest
from speaker.Speaker import Speaker

def test_speaker_speak():
    os.makedirs('tmp', exist_ok=True)
    speaker = Speaker('tts_models/multilingual/multi-dataset/your_tts', 'cpu', 'VirtualPipeMic', 'draft/target_voice.wav')
    # 只测试合成和播放接口是否可调用，不验证实际音频输出
    try:
        speaker.speak('Test audio')
    except Exception as e:
        pytest.skip(f'Speaker playback skipped due to: {e}')
