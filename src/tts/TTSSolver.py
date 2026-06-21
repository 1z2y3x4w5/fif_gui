import os
import re
import tempfile
from pathlib import Path
from typing import Optional

try:
    from TTS.api import TTS
except Exception:
    TTS = None  # lazy import handled in _ensure_tts

try:
    from num2words import num2words
except Exception:
    num2words = None


class TTSSolver:
    """TTS wrapper: lazy-initializes the TTS engine and provides
    helpers to write WAV files or return raw bytes.
    """

    def __init__(self, model: str, mode: str, target_voice_path: str):
        self.model = model
        self.target_voice_path = target_voice_path
        self._mode = mode
        self._tts = None

    def _ensure_tts(self) -> None:
        if self._tts is not None:
            return
        if TTS is None:
            raise RuntimeError("TTS package is not available. Please install requirements.")

        use_gpu = self._mode == "cuda"
        model_name = self.model or "tts_models/multilingual/multi-dataset/your_tts"

        if use_gpu:
            print("[TTS] 使用 GPU 加速初始化神经网络...")
            self._tts = TTS(model_name, progress_bar=False)
            self._tts.to("cuda")  # type: ignore
        else:
            print("[TTS] 使用 CPU 初始化神经网络（较慢）...")
            self._tts = TTS(model_name, progress_bar=False)
            self._tts.to("cpu")  # type: ignore

    def _normalize_currency_text(self, text: str) -> str:
        """将常见货币符号及金额转换为可读文本。

        支持示例：
        - $12.50 -> 12 dollars and 50 cents
        - ¥100 -> 100 yen
        - €3.20 -> 3 euros and 20 cents
        - £5 -> 5 pounds
        """

        if not text:
            return text

        # 去掉千位分隔符（逗号），例如 1,234.56
        def repl(match: re.Match) -> str:
            symbol = match.group('sym')
            amount = match.group('amt')
            # 移除逗号
            amount = amount.replace(',', '')
            if '.' in amount:
                integer_part, frac_part = amount.split('.', 1)
                # 取最多两位小数作为分
                frac = (frac_part + '00')[:2]
            else:
                integer_part = amount
                frac = ''

            # 支持常见货币符号及其全角变体
            symbol_map = {
                '$': 'dollar',
                '€': 'euro',
                '£': 'pound',
                '¥': 'yen',
                '￥': 'yuan',
                '￡': 'pound',
            }

            # ensure currency is a str (dict.get returns Optional)
            currency = symbol_map.get(symbol) or symbol

            # 将整数部分转换为单词（优先使用 num2words）
            try:
                int_part_val = int(integer_part) if integer_part != '' else 0
            except ValueError:
                int_part_val = 0

            if num2words is not None:
                try:
                    int_words = num2words(int_part_val, lang='en')
                except Exception:
                    int_words = str(int_part_val)
            else:
                int_words = str(int_part_val)

            # 复数化货币单位（yen/yuan 通常不加 s）
            if currency in ('yen', 'yuan'):
                currency_word = currency
            else:
                currency_word = currency + ('s' if int_part_val != 1 else '')

            if frac:
                if currency in ('yen', 'yuan'):
                    return f"{int_words} {currency_word}"
                try:
                    frac_val = int(frac)
                except ValueError:
                    frac_val = 0

                if frac_val == 0:
                    return f"{int_words} {currency_word}"

                if num2words is not None:
                    try:
                        frac_words = num2words(frac_val, lang='en')
                    except Exception:
                        frac_words = str(frac_val)
                else:
                    frac_words = str(frac_val)

                return f"{int_words} {currency_word} and {frac_words} cents"

            return f"{int_words} {currency_word}"

        # 匹配货币符号后面可选空格接数字，支持千位逗号和小数
        # include fullwidth pound sign '￡' (U+FFE1) in the symbol set
        pattern = re.compile(r"(?P<sym>[\$€£¥￥￡])\s*(?P<amt>[0-9][0-9,]*(?:\.[0-9]+)?)")
        return pattern.sub(repl, text)

    def _number_to_words(self, num_str: str) -> str:
        """Convert a numeric string to English words.

        - Integers: use num2words if available, else return digits.
        - Decimals: convert integer part to words, then 'point' + digit words.
        Examples:
          '1234' -> 'one thousand two hundred thirty-four'
          '12.50' -> 'twelve point five zero'
        """
        if not num_str:
            return num_str

        s = num_str.replace(',', '')
        if '.' in s:
            int_part, frac_part = s.split('.', 1)
        else:
            int_part, frac_part = s, ''

        # integer part
        int_words: str
        try:
            int_val = int(int_part) if int_part != '' else 0
        except ValueError:
            int_words = int_part
        else:
            if num2words is not None:
                try:
                    int_words = num2words(int_val, lang='en')
                except Exception:
                    int_words = str(int_val)
            else:
                int_words = str(int_val)

        if frac_part == '':
            return int_words

        # fractional part: speak as individual digits after 'point'
        digit_map = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
            '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
        }
        frac_words = ' '.join(digit_map.get(d, d) for d in frac_part)
        return f"{int_words} point {frac_words}"

    def _normalize_numbers(self, text: str) -> str:
        """Find numeric tokens and replace them with words.

        This runs after currency normalization so currency amounts are already words.
        """
        if not text:
            return text

        # Match numbers with optional commas and decimals (not part of words)
        pattern = re.compile(r"(?<!\w)(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?!\w)")

        def repl(match: re.Match) -> str:
            num = match.group('num')
            return self._number_to_words(num)

        return pattern.sub(repl, text)

    def get_voice(self, text: str) -> Optional[bytes]:
        """合成并返回 WAV 二进制数据；如果 text 为空或失败则返回 None。"""
        if not text:
            return None

        # 解决单词过少导致的bug
        if len(text.split()) <= 1:
            text = "Oh, " + text

        # 货币符号规范化，放在合成前
        text = self._normalize_currency_text(text)
        # 数字规范化（把纯数字转为单词）
        text = self._normalize_numbers(text)

        self._ensure_tts()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpf:
            tmp_path = tmpf.name

        try:
            self._tts.tts_to_file( # type: ignore
                text=text,
                speaker_wav=self.target_voice_path,
                language="en",
                file_path=tmp_path,
            )

            with open(tmp_path, "rb") as f:
                data = f.read()

            return data
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def get_file(self, text: str, path: str) -> None:
        """合成并将音频写到磁盘（覆盖）。"""
        if not text:
            return

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        print("[TTS] 正在合成语音...")
        # 货币符号规范化
        text = self._normalize_currency_text(text)
        # 数字规范化
        text = self._normalize_numbers(text)

        if len(text.split()) <= 1:
            text = "Oh, " + text

        self._ensure_tts()

        self._tts.tts_to_file( # type: ignore
            text=text,
            speaker_wav=self.target_voice_path,
            language="en",
            file_path=str(p),
        )