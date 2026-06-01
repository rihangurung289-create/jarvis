"""
Download the small English Vosk model for offline speech recognition.

Run once: python setup_vosk.py
"""

import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

import config

MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
ZIP_NAME = "vosk-model-small-en-us-0.15.zip"


def main() -> None:
    models_dir = Path(config.VOSK_MODEL_PATH).parent
    models_dir.mkdir(parents=True, exist_ok=True)
    target = Path(config.VOSK_MODEL_PATH)

    if target.is_dir():
        print(f"Model already exists at {target}")
        return

    zip_path = models_dir / ZIP_NAME
    print(f"Downloading Vosk model (~40 MB)...")
    print(f"URL: {MODEL_URL}")

    def progress(block_num: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            percent = min(100, block_num * block_size * 100 // total_size)
            print(f"\r  {percent}%", end="", flush=True)

    try:
        urlretrieve(MODEL_URL, zip_path, reporthook=progress)
    except Exception as exc:
        print(f"\nDownload failed: {exc}")
        print("Download manually from https://alphacephei.com/vosk/models")
        print(f"Extract to: {target}")
        sys.exit(1)

    print("\nExtracting...")
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(models_dir)

    extracted = models_dir / "vosk-model-small-en-us-0.15"
    if extracted != target and extracted.is_dir():
        if target.exists():
            shutil.rmtree(target)
        extracted.rename(target)

    zip_path.unlink(missing_ok=True)
    print(f"Done. Model ready at {target}")
    print('Set RECOGNITION_ENGINE = "vosk" in config.py to use offline mode.')


if __name__ == "__main__":
    main()
