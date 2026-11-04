"""Generate real EN/VI WAVs from bundled, hash-pinned MMS assets, offline.

Run during Linux image build/CI and isolated model-worker startup.
This module never imports the ASGI application, opens a ledger or contacts Modal.
"""
import argparse
import array
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import resource
import socket
import sys
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAX_RSS_MB = 2816  # Reserve 256 MiB of the isolated worker's 3072 MiB allocation.
SAMPLES = {'en': 'Play four beats slowly.', 'vi': 'Hãy chơi bốn phách chậm.'}


def _offline(*args, **kwargs):
    raise RuntimeError('MMS preflight attempted an outbound connection')


def input_cases(*, stress=False):
    cases = [(language, language, text) for language, text in SAMPLES.items()]
    if stress:
        from service.mms_tts import spoken_text
        for language, text in SAMPLES.items():
            words = spoken_text(text, language).split()
            selected = []
            while len(' '.join(selected + [words[len(selected) % len(words)]])) <= 240:
                selected.append(words[len(selected) % len(words)])
            cases.append((language + '-stress', language, ' '.join(selected)))
        cases.append(('vi-dense-stress', 'vi', 'la ' * 79 + 'sol'))
    return cases


def memory_usage():
    max_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    if max_rss_mb > MAX_RSS_MB:
        raise RuntimeError('MMS preflight exceeded 2816 MiB; isolated worker requires reserved headroom')
    return max_rss_mb


def verify_runtime(models, *, output=None, stress=False):
    """Return a warmed provider and redacted real-WAV receipt; fail before writes."""
    if platform.system() != 'Linux':
        raise RuntimeError('MMS CPU image preflight requires Linux; a Mac check is not acceptance')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    with patch.object(socket.socket, 'connect', _offline), patch.object(socket, 'create_connection', _offline):
        import numpy
        import torch
        import transformers
        if (torch.__version__, transformers.__version__, numpy.__version__) != ('2.9.0+cpu', '4.57.1', '2.2.6'):
            raise RuntimeError('MMS CPU dependency versions differ from the pinned image')
        if torch.version.cuda is not None or torch.cuda.is_available():
            raise RuntimeError('MMS runtime must use the CPU-only torch build')
        torch.set_num_threads(2)
        if torch.get_num_interop_threads() != 1:
            torch.set_num_interop_threads(1)
        from service.mms_tts import MmsSpeech, spoken_text
        from service.speech import validate_wav
        # Constructor verifies every manifest SHA256 before any model is loaded.
        speech = MmsSpeech(models)
        checks = {}
        recordings = {}
        for name, language, text in input_cases(stress=stress):
            normalized_length = len(spoken_text(text, language))
            if name.endswith('-stress') and not 230 <= normalized_length <= 240:
                raise RuntimeError('MMS stress input did not reach the supported normalized bound')
            audio = speech.synthesize(text, language)
            validate_wav(audio)
            with wave.open(io.BytesIO(audio), 'rb') as stream:
                if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 16000):
                    raise RuntimeError('MMS returned a noncanonical WAV')
                frames = stream.getnframes()
                pcm = array.array('h', stream.readframes(frames))
            if not pcm or not any(pcm):
                raise RuntimeError('MMS returned an empty or silent WAV')
            if any(parameter.device.type != 'cpu' for parameter in speech.models[language][1].parameters()):
                raise RuntimeError('MMS model escaped the CPU device')
            checks[name] = {'bytes': len(audio), 'frames': frames, 'sample_rate': 16000,
                                'normalized_characters': normalized_length,
                                'duration_ms': round(frames / 16), 'sha256': hashlib.sha256(audio).hexdigest()}
            recordings[name] = audio
            memory_usage()
        max_rss_mb = memory_usage()
        if output is not None:
            destination = Path(output)
            destination.mkdir(parents=True, exist_ok=True)
            for language, audio in recordings.items():
                descriptor = os.open(destination / (language + '.wav'), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(audio)
                    stream.flush()
                    os.fsync(stream.fileno())
        return speech, {'check': 'mms_cpu_runtime', 'result': 'PASS', 'platform': 'Linux',
                        'torch': torch.__version__, 'transformers': transformers.__version__,
                        'numpy': numpy.__version__, 'max_rss_mb': round(max_rss_mb, 1),
                        'memory_limit_mb': MAX_RSS_MB, 'stress_requested': stress,
                        'languages': checks, 'model_downloads': 0, 'provider_calls': 0,
                        'cloud_access': False, 'writer_permit_acquired': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='Optional new WAV files in an operator-selected directory')
    parser.add_argument('--stress', action='store_true', help='Build/CI: also synthesize EN/VI near the 240-character normalized limit')
    args = parser.parse_args()
    _, receipt = verify_runtime(args.models, output=args.output, stress=args.stress)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
