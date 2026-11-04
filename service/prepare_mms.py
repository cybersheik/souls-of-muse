"""Explicit download of the pinned public evaluation assets, verified by SHA256."""
import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path


def prepare(output):
    root = Path(output)
    catalog = json.loads(Path(__file__).with_name("mms_models.json").read_text())
    for language, manifest in catalog.items():
        target = root / language
        target.mkdir(parents=True, exist_ok=True)
        for filename, expected in manifest["files"].items():
            path = target / filename
            if path.exists():
                if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise ValueError(f"Existing {language}/{filename} differs; no overwrite performed")
                continue
            url = f"https://huggingface.co/{manifest['repo']}/resolve/{manifest['revision']}/{filename}"
            with tempfile.NamedTemporaryFile(dir=target) as temporary:
                digest = hashlib.sha256()
                size = 0
                with urllib.request.urlopen(url, timeout=90) as response:
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > 150_000_000:
                            raise ValueError("Unexpected MMS asset size")
                        digest.update(chunk); temporary.write(chunk)
                if digest.hexdigest() != expected:
                    raise ValueError(f"Checksum mismatch for {language}/{filename}")
                temporary.flush()
                # Keep temporary cleanup while making a durable asset copy.
                temporary.seek(0)
                with path.open("xb") as asset:
                    while chunk := temporary.read(1024 * 1024): asset.write(chunk)
        print(language, manifest["repo"], manifest["revision"], "verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Operator-selected evaluation directory")
    prepare(parser.parse_args().output)
