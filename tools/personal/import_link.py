#!/usr/bin/env python3
"""
Import a single social media link → fetch metadata + transcribe → stdout JSON.

Usage:
    python3 tools/import_link.py <url>

Output (stdout): JSON with keys: title, creator, platform, transcript, source_url, duration_sec
On error: JSON with key: error
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

BASE_DIR = Path(__file__).parent.parent
TRANSCRIBE_SCRIPT = BASE_DIR / "tools" / "transcribe_video.py"
PERSONAL_ENV = BASE_DIR / "projects" / "personal" / ".env"

_IMPERSONATE_TARGET = ImpersonateTarget("chrome")

_YT_COMMON = {
    "quiet": True,
    "impersonate": _IMPERSONATE_TARGET,
    "extractor_retries": 3,
}


def load_env():
    if PERSONAL_ENV.exists():
        for line in PERSONAL_ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def detect_platform(url: str) -> str:
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "tiktok.com" in u:
        return "tiktok"
    if "facebook.com" in u or "fb.com" in u or "fb.watch" in u:
        return "facebook"
    return "unknown"


def fetch_metadata(url: str) -> dict | None:
    ydl_opts = {**_YT_COMMON, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            return ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"ERROR fetch_metadata: {e}", file=sys.stderr)
            return None


def download_audio(url: str, out_dir: Path) -> Path | None:
    out_tmpl = str(out_dir / "audio.%(ext)s")
    ydl_opts = {
        **_YT_COMMON,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": out_tmpl,
        "postprocessors": [],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            print(f"ERROR download_audio: {e}", file=sys.stderr)
            return None
    for f in out_dir.iterdir():
        if f.name.startswith("audio."):
            return f
    return None


def transcribe(audio_path: Path, out_dir: Path) -> str:
    prefix = str(out_dir / "whisper")
    try:
        subprocess.run(
            ["python3", str(TRANSCRIBE_SCRIPT), str(audio_path), "--out", prefix],
            check=True,
            capture_output=True,
            timeout=600,
        )
    except subprocess.CalledProcessError as e:
        print(f"ERROR transcribe: {e.stderr.decode()[-300:]}", file=sys.stderr)
        return ""
    except subprocess.TimeoutExpired:
        print("ERROR transcribe: timeout", file=sys.stderr)
        return ""
    txt = Path(prefix + ".txt")
    return txt.read_text() if txt.exists() else ""


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No URL provided"}))
        sys.exit(0)

    url = sys.argv[1].strip()
    load_env()

    platform = detect_platform(url)

    meta = fetch_metadata(url)
    if not meta:
        print(json.dumps({"error": f"Could not fetch metadata for {url}"}))
        sys.exit(0)

    title = meta.get("title") or meta.get("fulltitle") or "Untitled"
    creator = meta.get("uploader") or meta.get("channel") or meta.get("creator") or ""
    duration_sec = int(meta.get("duration") or 0)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        audio_path = download_audio(url, tmp_dir)
        if not audio_path:
            print(json.dumps({"error": "Audio download failed"}))
            sys.exit(0)

        transcript = transcribe(audio_path, tmp_dir)

    print(json.dumps({
        "title": title,
        "creator": creator,
        "platform": platform,
        "transcript": transcript,
        "source_url": url,
        "duration_sec": duration_sec,
    }))


if __name__ == "__main__":
    main()
