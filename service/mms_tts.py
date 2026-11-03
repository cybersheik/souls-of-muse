"""Pinned Meta MMS-TTS evaluation. No downloads or remote code at runtime."""
import hashlib
import importlib.util
import io
import json
import re
import unicodedata
import wave
from pathlib import Path

from .speech import MAX_TEXT, validate_wav


def spoken_text(text, language):
    """Expand musical quantities before MMS normalization can discard digits."""
    if language not in ("en", "vi") or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("unsupported_speech_text")
    from num2words import num2words
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"\bbpm\b", "beats per minute" if language == "en" else "nhịp mỗi phút", text)
    # A quantity can touch its unit, e.g. 60bpm.
    text = re.sub(r"(?<=\d)bpm\b", " beats per minute" if language == "en" else " nhịp mỗi phút", text)
    text = re.sub(r"(?<=\d)\s*[-–—]\s*(?=\d)", " to " if language == "en" else " đến ", text)
    text = re.sub(r"[-−](?=\d)", " minus " if language == "en" else " âm ", text)
    def number(match):
        raw = match.group()
        group, decimal = (",", ".") if language == "en" else (".", ",")
        grouped = rf"\d{{1,3}}(?:{re.escape(group)}\d{{3}})+(?:{re.escape(decimal)}\d+)?"
        plain = rf"\d+(?:{re.escape(decimal)}\d+)?"
        if not re.fullmatch(grouped if group in raw else plain, raw):
            raise ValueError("ambiguous_speech_quantity")
        parts = raw.replace(group, "").split(decimal)
        value = int(parts[0])
        if value > 999_999 or (len(parts) > 1 and len(parts[1]) > 6):
            raise ValueError("unsupported_speech_quantity")
        words = num2words(value, lang=language)
        if len(parts) > 1:
            words += (" point " if language == "en" else " phẩy ") + " ".join(num2words(int(digit), lang=language) for digit in parts[1])
        return " " + words + " "
    text = re.sub(r"\d+(?:[.,]\d+)*", number, text)
    replacements = {"#": ("sharp", "thăng"), "♯": ("sharp", "thăng"),
                    "♭": ("flat", "giáng"), "/": ("over", "trên"),
                    "+": ("plus", "cộng"), "%": ("percent", "phần trăm"),
                    "&": ("and", "và"), "=": ("equals", "bằng")}
    for symbol, words in replacements.items():
        text = text.replace(symbol, " " + words[language == "vi"] + " ")
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r'[.,!?;:()\[\]{}"“”«»…—]', " ", text)
    text = " ".join(text.split())
    if not text or len(text) > 700:
        raise ValueError("unsupported_speech_text")
    return text


class MmsSpeech:
    def __init__(self, root):
        self.root = Path(root)
        self.catalog = json.loads(Path(__file__).with_name("mms_models.json").read_text())
        for language, manifest in self.catalog.items():
            for filename, digest in manifest["files"].items():
                path = self.root / language / filename
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise ValueError("missing_or_changed_mms_asset")
        self.revision = "mms-normalization-v2:" + ":".join(self.catalog[lang]["revision"] for lang in ("en", "vi"))
        self.models = {}

    @classmethod
    def from_environ(cls, env):
        # This is an opt-in technical evaluation under CC-BY-NC 4.0. Public or
        # commercial release requires a separately resolved deployment choice.
        if env.get("SOM_MMS_TTS_EVALUATION") != "1" or not env.get("SOM_MMS_TTS_DIR"):
            return None
        if any(importlib.util.find_spec(module) is None for module in ("torch", "transformers", "num2words")):
            return None
        try:
            return cls(env["SOM_MMS_TTS_DIR"])
        except (ValueError, OSError):
            return None

    def synthesize(self, text, language):
        import numpy as np
        import torch
        from transformers import VitsModel, VitsTokenizer
        normalized = spoken_text(text, language)
        torch.set_num_threads(2)
        if language not in self.models:
            path = self.root / language
            tokenizer = VitsTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
            model = VitsModel.from_pretrained(path, local_files_only=True, trust_remote_code=False, use_safetensors=True).eval()
            self.models[language] = tokenizer, model
        tokenizer, model = self.models[language]
        # Fail before inference if MMS would silently omit a letter, symbol or
        # number. Punctuation and supported quantities were handled above.
        if any(char not in tokenizer.get_vocab() for char in normalized):
            raise ValueError("unsupported_speech_character")
        encoded = tokenizer(normalized, return_tensors="pt")
        with torch.random.fork_rng(devices=[]), torch.inference_mode():
            torch.manual_seed(7)
            values = model(**encoded).waveform[0].cpu().numpy()
        if not np.isfinite(values).all() or not np.any(values):
            raise ValueError("invalid_speech_waveform")
        if model.config.sampling_rate != 16000:
            raise ValueError("invalid_speech_sample_rate")
        pcm = (np.clip(values, -1, 1) * 32767).astype("<i2").tobytes()
        output = io.BytesIO()
        with wave.open(output, "wb") as recording:
            recording.setnchannels(1); recording.setsampwidth(2); recording.setframerate(16000)
            recording.writeframes(pcm)
        result = output.getvalue()
        validate_wav(result)
        return result
