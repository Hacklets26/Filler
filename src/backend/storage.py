import re
from pathlib import Path

VIDEO_DIRECTORY = Path(__file__).resolve().parent / "videos"
VIDEO_DIRECTORY.mkdir(parents=True, exist_ok=True)

VIDEO_URL_RE = re.compile(r"^https?://[^/\s]+/videos/([0-9a-f]{32}\.mp4)$")


def delete_video_file(video_url: str | None) -> None:
    match = VIDEO_URL_RE.match(video_url or "")
    if match:
        (VIDEO_DIRECTORY / match.group(1)).unlink(missing_ok=True)
