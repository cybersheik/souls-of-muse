"""Opt-in macOS installed voices for the local supervised lesson.

No model download, provider key, shell command, or microphone access. Only the
existing approved-translation speech route supplies text to this adapter.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .speech import MAX_TEXT, validate_wav


class NativeSpeech:
    revision = "macos-installed-say-Daniel-Linh-pcm16-16000-v1"
    voices = {"en": "Daniel", "vi": "Linh"}

    def __init__(self, cache_dir="/private/tmp/cx1-som-native-speech"):
        if sys.platform != "darwin" or not Path("/usr/bin/say").is_file():
            raise ValueError("native_speech_unavailable")
        self.cache_dir = Path(cache_dir)
        if not self.cache_dir.is_absolute() or self.cache_dir.is_symlink():
            raise ValueError("invalid_speech_cache")
        self.cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    @classmethod
    def from_environ(cls, env):
        if env.get("SOM_NATIVE_TTS") != "1":
            return None
        return cls(env.get("SOM_NATIVE_TTS_CACHE", "/private/tmp/cx1-som-native-speech"))

    def synthesize(self, text, language):
        if language not in self.voices or not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT or "\0" in text:
            raise ValueError("unsupported_speech_text")
        fd, name = tempfile.mkstemp(prefix="speech-", suffix=".wav", dir=self.cache_dir)
        os.close(fd)
        try:
            # Text goes through stdin, so leading '-' and shell syntax remain
            # spoken data rather than command options or executable code.
            subprocess.run(["/usr/bin/say", "-v", self.voices[language], "-o", name,
                            "--file-format=WAVE", "--data-format=LEI16@16000"],
                           input=text, text=True, check=True, timeout=25,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            audio = Path(name).read_bytes()
            validate_wav(audio)
            return audio
        finally:
            # Only this request's exclusive temporary audio file is removed.
            # No directory, model asset, or project file is deleted.
            Path(name).unlink(missing_ok=True)
