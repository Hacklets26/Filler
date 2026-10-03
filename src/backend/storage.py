from pathlib import Path


VIDEO_DIRECTORY = Path(__file__).resolve().parent / "videos"
VIDEO_DIRECTORY.mkdir(parents=True, exist_ok=True)
