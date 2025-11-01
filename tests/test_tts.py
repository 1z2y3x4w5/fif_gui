import os
import pytest
from tts.TTSSolver import TTSSolver

def test_tts_get_voice():
    os.makedirs('tmp', exist_ok=True)
    solver = TTSSolver('tts_models/multilingual/multi-dataset/your_tts', 'cpu', 'draft/target_voice.wav')
    data = solver.get_voice('Hello world')
    assert data is not None and isinstance(data, bytes)
    with open('tmp/test_tts.wav', 'wb') as f:
        f.write(data)
    assert os.path.exists('tmp/test_tts.wav')
