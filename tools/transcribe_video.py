#!/usr/bin/env python3
"""Transcribe a video/audio file using whisper.cpp.

Usage:
  python3 tools/transcribe_video.py <input_file> [--out <out_prefix>] [--model <path>]

Default model: ~/.cache/hyperframes/whisper/models/ggml-small.en.bin

Outputs (alongside --out prefix, or next to input if omitted):
  <prefix>.wav         — 16kHz mono PCM (whisper requirement)
  <prefix>.json        — whisper-cli --output-json-full (word-level timestamps)
  <prefix>.srt         — subtitle file
  <prefix>.txt         — plain transcript

Requires: ffmpeg + whisper-cli on PATH.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = Path.home() / ".cache/hyperframes/whisper/models/ggml-small.en.bin"


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def check_deps():
    for bin_name in ("ffmpeg", "whisper-cli"):
        if shutil.which(bin_name) is None:
            die(f"{bin_name} not on PATH. Install via: brew install {'ffmpeg' if bin_name == 'ffmpeg' else 'whisper-cpp'}")


def extract_wav(src: Path, dst_wav: Path):
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-ac", "1", "-ar", "16000", "-vn",
        "-acodec", "pcm_s16le", str(dst_wav),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_whisper(wav: Path, out_prefix: Path, model: Path):
    cmd = [
        "whisper-cli",
        "-m", str(model),
        "-f", str(wav),
        "-of", str(out_prefix),
        "-ojf",       # JSON full (word-level timings)
        "-osrt",      # SRT
        "-otxt",      # plain text
        "-ml", "0",   # no max segment length
        "-t", "8",    # threads
    ]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Video or audio file (.mov/.mp4/.wav/.mp3/...)")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output prefix (no extension). Default: next to input.")
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL,
                    help=f"Whisper model path (default: {DEFAULT_MODEL})")
    args = ap.parse_args()

    check_deps()

    src = args.input.resolve()
    if not src.exists():
        die(f"Input not found: {src}")
    if not args.model.exists():
        die(f"Model not found: {args.model}. Download a ggml model first.")

    out_prefix = args.out.resolve() if args.out else src.with_suffix("")
    out_prefix.parent.mkdir(parents=True, exist_ok=True)

    wav_path = out_prefix.with_suffix(".wav")
    print(f"[1/2] Extracting audio → {wav_path}")
    extract_wav(src, wav_path)

    print(f"[2/2] Transcribing with whisper.cpp (model={args.model.name})")
    run_whisper(wav_path, out_prefix, args.model)

    print()
    print("Done. Outputs:")
    for ext in (".json", ".srt", ".txt", ".wav"):
        p = out_prefix.with_suffix(ext)
        if p.exists():
            print(f"  {p}")


if __name__ == "__main__":
    main()
