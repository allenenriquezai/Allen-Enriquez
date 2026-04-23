#!/usr/bin/env python3
"""
Video editing pipeline for Allen's personal brand content.
Hormozi-style editing: silence removal, captions, punch-in zooms,
B-roll inserts, SFX, color grading.

Usage:
    python3 tools/edit_video.py --input raw.mp4 --type reel
    python3 tools/edit_video.py --input raw.mp4 --type youtube --music bg.mp3
    python3 tools/edit_video.py --input raw.mp4 --type reel --captions off
    python3 tools/edit_video.py check-deps          # verify dependencies
    python3 tools/edit_video.py generate-sfx         # create synthetic SFX
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp" / "videos"
SFX_DIR = PROJECT_ROOT / "tools" / "assets" / "sfx"

# Ensure user-local Python bin and Homebrew are on PATH
_extra_paths = [
    str(Path.home() / "Library" / "Python" / "3.9" / "bin"),
    "/opt/homebrew/bin",
    "/usr/local/bin",
]
for p in _extra_paths:
    if p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + ":" + os.environ.get("PATH", "")

SILENCE_THRESHOLD_DB = -30
SILENCE_MIN_DURATION = 0.4

CAPTION_FONT = "Anton"
CAPTION_FALLBACK_FONT = "Montserrat-Bold"
CAPTION_MAX_CHARS_PER_LINE = 15
CAPTION_MAX_LINES = 2
CAPTION_WORDS_PER_DISPLAY = 5

ZOOM_SCALE = 1.2
ZOOM_DURATION_SEC = 4

COLOR_SATURATION = 1.3
COLOR_CONTRAST = 1.1
COLOR_BRIGHTNESS = 0.05

MUSIC_VOLUME_DB = -20

ASPECT_RATIOS = {
    "reel": {"w": 1080, "h": 1920, "label": "9:16"},
    "youtube": {"w": 1920, "h": 1080, "label": "16:9"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run(cmd, capture=True, check=True):
    """Run a shell command, return stdout."""
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str), capture_output=capture,
        text=True, check=check
    )
    return result.stdout.strip() if capture else ""


def ffprobe_duration(path):
    """Get video duration in seconds."""
    out = run(
        f'ffprobe -v error -show_entries format=duration '
        f'-of default=noprint_wrappers=1:nokey=1 "{path}"'
    )
    return float(out)


def ffprobe_resolution(path):
    """Get video width and height."""
    out = run(
        f'ffprobe -v error -select_streams v:0 '
        f'-show_entries stream=width,height '
        f'-of csv=s=x:p=0 "{path}"'
    )
    w, h = out.split("x")
    return int(w), int(h)


def file_size_mb(path):
    return round(os.path.getsize(path) / (1024 * 1024), 1)


def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60]


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
DEPS = {
    "ffmpeg": {"check": "ffmpeg -version", "install": "brew install ffmpeg"},
    "ffprobe": {"check": "ffprobe -version", "install": "(included with ffmpeg)"},
    "whisper": {"check": "whisper --help", "install": "pip install openai-whisper"},
    "auto-editor": {"check": "auto-editor --help", "install": "pip install auto-editor"},
}


def check_deps(install=False):
    """Check and optionally install dependencies. Returns True if all present."""
    missing = []
    for name, info in DEPS.items():
        try:
            subprocess.run(
                info["check"], shell=True, capture_output=True, check=True
            )
            print(f"  [OK] {name}")
        except subprocess.CalledProcessError:
            print(f"  [MISSING] {name} — install with: {info['install']}")
            missing.append(name)

    if missing and install:
        print("\nInstalling missing dependencies...")
        for name in missing:
            if name == "ffprobe":
                continue  # comes with ffmpeg
            cmd = DEPS[name]["install"]
            print(f"  Running: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
        print("Done. Re-run check-deps to verify.")

    return len(missing) == 0


# ---------------------------------------------------------------------------
# SFX Generation (synthetic, zero downloads)
# ---------------------------------------------------------------------------
def generate_sfx():
    """Generate synthetic SFX using ffmpeg. No downloads needed."""
    ensure_dir(SFX_DIR)

    sfx = {
        "whoosh.wav": (
            'ffmpeg -y -f lavfi -i "anoisesrc=d=0.4:c=pink:r=44100:a=0.3" '
            '-af "afade=t=in:ss=0:d=0.1,afade=t=out:st=0.2:d=0.2,'
            'highpass=f=800,lowpass=f=4000" '
            f'"{SFX_DIR}/whoosh.wav"'
        ),
        "pop.wav": (
            'ffmpeg -y -f lavfi -i "sine=frequency=800:duration=0.08" '
            '-af "afade=t=out:st=0.03:d=0.05,volume=0.5" '
            f'"{SFX_DIR}/pop.wav"'
        ),
        "click.wav": (
            'ffmpeg -y -f lavfi -i "sine=frequency=1200:duration=0.05" '
            '-af "afade=t=out:st=0.02:d=0.03,volume=0.4" '
            f'"{SFX_DIR}/click.wav"'
        ),
        "swoosh.wav": (
            'ffmpeg -y -f lavfi -i "anoisesrc=d=0.6:c=white:r=44100:a=0.2" '
            '-af "afade=t=in:ss=0:d=0.15,afade=t=out:st=0.3:d=0.3,'
            'highpass=f=1000,lowpass=f=6000,atempo=1.3" '
            f'"{SFX_DIR}/swoosh.wav"'
        ),
    }

    for name, cmd in sfx.items():
        print(f"  Generating {name}...")
        subprocess.run(cmd, shell=True, capture_output=True, check=True)
    print(f"  SFX saved to {SFX_DIR}")


# ---------------------------------------------------------------------------
# Pipeline Steps
# ---------------------------------------------------------------------------

def step_transcribe(input_path, output_dir, whisper_model="base"):
    """Transcribe video with Whisper. Returns transcript data."""
    print("\n[1/7] Transcribing with Whisper...")
    transcript_dir = ensure_dir(output_dir / "whisper")

    run(
        f'whisper "{input_path}" --model {whisper_model} '
        f'--output_format json --output_dir "{transcript_dir}" '
        f'--language en'
    )

    # Find the output JSON
    json_files = list(Path(transcript_dir).glob("*.json"))
    if not json_files:
        print("  ERROR: Whisper produced no output")
        sys.exit(1)

    with open(json_files[0]) as f:
        transcript = json.load(f)

    # Also save plain text
    text_lines = []
    for seg in transcript.get("segments", []):
        start = seg["start"]
        text = seg["text"].strip()
        mins = int(start // 60)
        secs = start % 60
        text_lines.append(f"[{mins:02d}:{secs:05.2f}] {text}")

    transcript_path = output_dir / "transcript.txt"
    transcript_path.write_text("\n".join(text_lines))
    print(f"  Transcript saved: {transcript_path}")
    print(f"  Segments: {len(transcript.get('segments', []))}")

    return transcript


def step_remove_silence(input_path, output_dir):
    """Remove silence using auto-editor. Returns path to trimmed file."""
    print("\n[2/7] Removing silence...")
    trimmed = output_dir / "trimmed.mp4"

    run(
        f'auto-editor "{input_path}" '
        f'--margin 0.1s '
        f'--output "{trimmed}" '
        f'--no-open'
    )

    orig_dur = ffprobe_duration(input_path)
    new_dur = ffprobe_duration(str(trimmed))
    cut_pct = round((1 - new_dur / orig_dur) * 100, 1)
    print(f"  Original: {orig_dur:.1f}s → Trimmed: {new_dur:.1f}s ({cut_pct}% cut)")

    return str(trimmed)


def step_generate_captions(transcript, output_dir, video_type):
    """Generate ASS subtitle file from Whisper transcript. Returns ASS path."""
    print("\n[3/7] Generating captions...")

    segments = transcript.get("segments", [])
    if not segments:
        print("  No segments found, skipping captions")
        return None

    # ASS header — Hormozi style: uppercase, bold, centered bottom third
    ass_path = output_dir / "captions.ass"
    ar = ASPECT_RATIOS[video_type]
    play_res_x, play_res_y = ar["w"], ar["h"]

    # Vertical margin: bottom 15% of frame
    margin_bottom = int(play_res_y * 0.12)

    ass_content = f"""[Script Info]
Title: Captions
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{CAPTION_FONT},72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,0,2,40,40,{margin_bottom},1
Style: Highlight,{CAPTION_FONT},72,&H0000D4FF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,4,0,2,40,40,{margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    # Build word-by-word captions from segments
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # Fall back to segment-level caption
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            text = seg["text"].strip().upper()
            # Chunk long text
            text_words = text.split()
            for i in range(0, len(text_words), CAPTION_WORDS_PER_DISPLAY):
                chunk = " ".join(text_words[i:i + CAPTION_WORDS_PER_DISPLAY])
                if len(chunk) > CAPTION_MAX_CHARS_PER_LINE * CAPTION_MAX_LINES:
                    chunk = chunk[:CAPTION_MAX_CHARS_PER_LINE * CAPTION_MAX_LINES]
                ass_content += (
                    f"Dialogue: 0,{start},{end},Default,,0,0,0,,"
                    f"{chunk}\n"
                )
            continue

        # Word-level timing available — highlight active word
        for i in range(0, len(words), CAPTION_WORDS_PER_DISPLAY):
            chunk_words = words[i:i + CAPTION_WORDS_PER_DISPLAY]
            chunk_start = format_time(chunk_words[0].get("start", seg["start"]))
            chunk_end = format_time(chunk_words[-1].get("end", seg["end"]))

            # Build text with word highlighting via karaoke tags
            display_parts = []
            for w in chunk_words:
                word_text = w.get("word", "").strip().upper()
                if word_text:
                    display_parts.append(word_text)

            display_text = " ".join(display_parts)

            # Enforce line length limits
            if len(display_text) > CAPTION_MAX_CHARS_PER_LINE * CAPTION_MAX_LINES + 1:
                mid = len(display_parts) // 2
                line1 = " ".join(display_parts[:mid])
                line2 = " ".join(display_parts[mid:])
                display_text = f"{line1}\\N{line2}"

            ass_content += (
                f"Dialogue: 0,{chunk_start},{chunk_end},Default,,0,0,0,,"
                f"{display_text}\n"
            )

    ass_path.write_text(ass_content)
    print(f"  Captions saved: {ass_path}")
    return str(ass_path)


def step_apply_zooms(input_path, transcript, output_dir, video_type):
    """Apply punch-in zooms on key points. Returns path to zoomed video."""
    print("\n[4/7] Applying punch-in zooms...")

    segments = transcript.get("segments", [])
    if not segments:
        print("  No segments, skipping zooms")
        return input_path

    ar = ASPECT_RATIOS[video_type]
    w, h = ar["w"], ar["h"]

    # Identify zoom points: longer segments (key points) get zooms
    # Sort by text length (proxy for importance) and pick top 30%
    scored = sorted(segments, key=lambda s: len(s.get("text", "")), reverse=True)
    zoom_count = max(1, len(scored) // 3)
    zoom_segments = sorted(scored[:zoom_count], key=lambda s: s["start"])

    if not zoom_segments:
        return input_path

    zoomed = str(output_dir / "zoomed.mp4")

    # Build zoompan filter for each zoom segment
    # We use a complex approach: overlay zoom sections onto the base video
    # Simpler approach: apply zoompan to entire video at marked timestamps
    # using the sendcmd filter to trigger zoom at specific times

    # Build a filtergraph that zooms during key segments
    zoom_filters = []
    for seg in zoom_segments:
        start = seg["start"]
        end = seg["end"]
        dur = end - start
        if dur < 1:
            continue
        # Smooth zoom in, hold, then cut back
        zoom_filters.append(
            f"between(t,{start},{end})"
        )

    if not zoom_filters:
        return input_path

    zoom_condition = "+".join(zoom_filters)

    # zoompan: zoom in when condition met, normal otherwise
    # Using the crop filter approach: crop to center with scale
    filter_str = (
        f"scale={int(w * ZOOM_SCALE)}:{int(h * ZOOM_SCALE)},"
        f"crop={w}:{h}:"
        f"(iw-{w})/2*(1-({zoom_condition})):"
        f"(ih-{h})/2*(1-({zoom_condition})),"
        f"scale={w}:{h}"
    )

    # Simpler approach: use setpts + overlay with zoom
    # Actually, let's use the crop-based zoom which is more reliable
    filter_cmd = (
        f"[0:v]split=2[base][zoom];"
        f"[zoom]scale={int(w * ZOOM_SCALE)}:{int(h * ZOOM_SCALE)},"
        f"crop={w}:{h}:(iw-{w})/2:(ih-{h})/2[zoomed];"
        f"[base][zoomed]overlay=0:0:enable='{'+'.join(zoom_filters)}'[out]"
    )

    run(
        f'ffmpeg -y -i "{input_path}" '
        f'-filter_complex "{filter_cmd}" '
        f'-map "[out]" -map 0:a -c:a copy '
        f'-c:v libx264 -preset fast -crf 18 "{zoomed}"'
    )

    print(f"  Applied {len(zoom_filters)} zoom sections")
    return zoomed


def step_insert_broll(input_path, broll_dir, transcript, output_dir, video_type):
    """Insert B-roll clips at regular intervals. Returns path to result."""
    print("\n[5/7] Inserting B-roll...")

    if not broll_dir or not Path(broll_dir).exists():
        print("  No B-roll directory provided, skipping")
        return input_path

    broll_files = sorted(Path(broll_dir).glob("*.*"))
    broll_files = [f for f in broll_files if f.suffix.lower() in
                   ('.mp4', '.mov', '.png', '.jpg', '.jpeg', '.excalidraw')]
    if not broll_files:
        print("  No B-roll files found, skipping")
        return input_path

    ar = ASPECT_RATIOS[video_type]
    w, h = ar["w"], ar["h"]
    duration = ffprobe_duration(input_path)

    # Place B-roll every 20-30 seconds
    interval = 25  # seconds between B-roll
    insert_points = []
    t = interval
    broll_idx = 0
    while t < duration - 5 and broll_idx < len(broll_files):
        insert_points.append({"time": t, "file": str(broll_files[broll_idx])})
        broll_idx = (broll_idx + 1) % len(broll_files)
        t += interval

    if not insert_points:
        return input_path

    # For images: overlay for 3 seconds at each point
    # For videos: cut and splice
    result = input_path
    overlay_filters = []

    for i, point in enumerate(insert_points):
        broll_path = point["file"]
        t = point["time"]

        if broll_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            overlay_filters.append({
                "input": broll_path,
                "start": t,
                "duration": 3,
                "type": "image"
            })

    if overlay_filters:
        output = str(output_dir / "with_broll.mp4")
        inputs = f'-i "{input_path}"'
        filter_parts = []
        current = "0:v"

        for i, ov in enumerate(overlay_filters):
            inp_idx = i + 1
            inputs += f' -i "{ov["input"]}"'
            scaled = f"broll{i}"
            overlay_out = f"ov{i}"
            filter_parts.append(
                f'[{inp_idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,'
                f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[{scaled}]'
            )
            filter_parts.append(
                f'[{current}][{scaled}]overlay=0:0:'
                f'enable=\'between(t,{ov["start"]},{ov["start"] + ov["duration"]})\''
                f'[{overlay_out}]'
            )
            current = overlay_out

        filter_str = ";".join(filter_parts)
        run(
            f'ffmpeg -y {inputs} '
            f'-filter_complex "{filter_str}" '
            f'-map "[{current}]" -map 0:a -c:a copy '
            f'-c:v libx264 -preset fast -crf 18 "{output}"'
        )
        result = output
        print(f"  Inserted {len(overlay_filters)} B-roll overlays")
    else:
        print("  B-roll files are video, splicing not yet implemented — skipping")

    return result


def step_add_sfx_and_music(input_path, output_dir, music_path=None):
    """Add SFX on transitions and optional background music. Returns path."""
    print("\n[6/7] Adding SFX and music...")

    whoosh = SFX_DIR / "whoosh.wav"
    pop = SFX_DIR / "pop.wav"

    has_sfx = whoosh.exists() and pop.exists()
    if not has_sfx and not music_path:
        print("  No SFX files or music, skipping. Run 'generate-sfx' first.")
        return input_path

    output = str(output_dir / "with_audio.mp4")
    duration = ffprobe_duration(input_path)

    inputs = f'-i "{input_path}"'
    filter_parts = []
    audio_streams = ["[0:a]"]
    inp_idx = 1

    # Add background music if provided
    if music_path and Path(music_path).exists():
        inputs += f' -i "{music_path}"'
        # Loop music to match video duration, reduce volume
        filter_parts.append(
            f'[{inp_idx}:a]aloop=loop=-1:size=2e+09,'
            f'atrim=0:{duration},'
            f'volume={10 ** (MUSIC_VOLUME_DB / 20):.4f}[music]'
        )
        audio_streams.append("[music]")
        inp_idx += 1

    # Add whoosh at ~30s intervals (section transitions)
    if has_sfx:
        whoosh_times = list(range(30, int(duration) - 5, 30))
        if whoosh_times:
            inputs += f' -i "{whoosh}"'
            delays = "|".join(
                f"{int(t * 1000)}|{int(t * 1000)}" for t in whoosh_times
            )
            filter_parts.append(
                f'[{inp_idx}:a]asplit={len(whoosh_times)}'
                + "".join(f'[wh{i}]' for i in range(len(whoosh_times)))
            )
            for i, t in enumerate(whoosh_times):
                delay_ms = int(t * 1000)
                filter_parts.append(
                    f'[wh{i}]adelay={delay_ms}|{delay_ms}[whd{i}]'
                )
                audio_streams.append(f'[whd{i}]')
            inp_idx += 1

    if len(audio_streams) <= 1:
        print("  Nothing to mix, skipping")
        return input_path

    # Mix all audio streams
    mix_inputs = "".join(audio_streams)
    filter_parts.append(
        f'{mix_inputs}amix=inputs={len(audio_streams)}:'
        f'duration=first:dropout_transition=2[aout]'
    )

    filter_str = ";".join(filter_parts)
    run(
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_str}" '
        f'-map 0:v -map "[aout]" '
        f'-c:v copy -c:a aac -b:a 192k "{output}"'
    )

    print(f"  Audio mixed ({len(audio_streams)} streams)")
    return output


def step_color_grade_and_export(input_path, output_dir, video_type,
                                 captions_path=None):
    """Apply color grading, burn captions, final export. Returns path."""
    print("\n[7/7] Color grading and final export...")

    ar = ASPECT_RATIOS[video_type]
    w, h = ar["w"], ar["h"]
    output = str(output_dir / "final.mp4")

    # Build video filter chain
    vf_parts = []

    # Scale to target resolution
    vf_parts.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease")
    vf_parts.append(f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")

    # Color grading
    vf_parts.append(
        f"eq=saturation={COLOR_SATURATION}:"
        f"contrast={COLOR_CONTRAST}:"
        f"brightness={COLOR_BRIGHTNESS}"
    )

    # Burn captions
    if captions_path and Path(captions_path).exists():
        # Escape path for ffmpeg filter
        esc_path = captions_path.replace("'", "'\\''").replace(":", "\\:")
        vf_parts.append(f"ass='{esc_path}'")

    vf = ",".join(vf_parts)

    # Export settings
    if video_type == "reel":
        # Reels: optimize for mobile, smaller file
        crf = 20
        preset = "medium"
    else:
        # YouTube: higher quality
        crf = 18
        preset = "slow"

    run(
        f'ffmpeg -y -i "{input_path}" '
        f'-vf "{vf}" '
        f'-c:v libx264 -preset {preset} -crf {crf} '
        f'-c:a aac -b:a 192k '
        f'-movflags +faststart '
        f'"{output}"'
    )

    print(f"  Exported: {output}")
    return output


# ---------------------------------------------------------------------------
# Edit Log
# ---------------------------------------------------------------------------
def write_edit_log(output_dir, input_path, final_path, transcript, video_type,
                   steps_run):
    """Write edit_log.json and timeline.md."""
    orig_dur = ffprobe_duration(input_path)
    final_dur = ffprobe_duration(final_path)

    log = {
        "input": str(input_path),
        "output": str(final_path),
        "type": video_type,
        "original_duration_sec": round(orig_dur, 2),
        "final_duration_sec": round(final_dur, 2),
        "cut_percentage": round((1 - final_dur / orig_dur) * 100, 1),
        "original_size_mb": file_size_mb(input_path),
        "final_size_mb": file_size_mb(final_path),
        "segments": len(transcript.get("segments", [])),
        "steps": steps_run,
    }

    log_path = output_dir / "edit_log.json"
    log_path.write_text(json.dumps(log, indent=2))

    # Timeline
    timeline_lines = [
        f"# Edit Timeline — {Path(input_path).name}",
        f"",
        f"**Type:** {video_type}",
        f"**Original:** {orig_dur:.1f}s ({file_size_mb(input_path)} MB)",
        f"**Final:** {final_dur:.1f}s ({file_size_mb(final_path)} MB)",
        f"**Cut:** {log['cut_percentage']}%",
        f"",
        "## Transcript Segments",
        "",
    ]
    for seg in transcript.get("segments", []):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        timeline_lines.append(f"- [{start:.1f}s - {end:.1f}s] {text}")

    timeline_lines.extend(["", "## Steps Applied", ""])
    for step in steps_run:
        timeline_lines.append(f"- {step}")

    timeline_path = output_dir / "timeline.md"
    timeline_path.write_text("\n".join(timeline_lines))

    print(f"\n  edit_log.json: {log_path}")
    print(f"  timeline.md:   {timeline_path}")
    return log


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(args):
    """Execute the full editing pipeline."""
    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    video_type = args.type
    slug = slugify(Path(input_path).stem)
    output_dir = Path(ensure_dir(TMP_DIR / slug))

    print(f"{'=' * 60}")
    print(f"  Video Edit Pipeline — {video_type.upper()}")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  Style:  {args.style}")
    print(f"{'=' * 60}")

    ar = ASPECT_RATIOS[video_type]
    print(f"\n  Target: {ar['label']} ({ar['w']}x{ar['h']})")
    print(f"  Size:   {file_size_mb(input_path)} MB")
    print(f"  Length: {ffprobe_duration(input_path):.1f}s")

    steps_run = []
    current = input_path

    # Step 1: Transcribe
    transcript = step_transcribe(input_path, output_dir,
                                  whisper_model=args.whisper_model)
    steps_run.append("transcribe")

    # Step 2: Remove silence
    current = step_remove_silence(current, output_dir)
    steps_run.append("silence_removal")

    # Step 3: Captions
    captions_path = None
    if args.captions == "on":
        captions_path = step_generate_captions(transcript, output_dir, video_type)
        steps_run.append("captions")
    else:
        print("\n[3/7] Captions: OFF (skipped)")

    # Step 4: Punch-in zooms
    if not args.no_zoom:
        current = step_apply_zooms(current, transcript, output_dir, video_type)
        steps_run.append("punch_in_zoom")
    else:
        print("\n[4/7] Zooms: OFF (skipped)")

    # Step 5: B-roll
    current = step_insert_broll(current, args.broll, transcript, output_dir,
                                 video_type)
    if args.broll:
        steps_run.append("broll_insert")

    # Step 6: SFX + Music
    current = step_add_sfx_and_music(current, output_dir,
                                      music_path=args.music)
    steps_run.append("sfx_music")

    # Step 7: Color grade + Export
    final = step_color_grade_and_export(current, output_dir, video_type,
                                         captions_path=captions_path)
    steps_run.append("color_grade_export")

    # Write logs
    log = write_edit_log(output_dir, input_path, final, transcript,
                          video_type, steps_run)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  DONE")
    print(f"  Final:    {final}")
    print(f"  Duration: {log['original_duration_sec']}s → {log['final_duration_sec']}s")
    print(f"  Size:     {log['original_size_mb']} MB → {log['final_size_mb']} MB")
    print(f"  Cut:      {log['cut_percentage']}%")
    print(f"{'=' * 60}")

    return final


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Video editing pipeline — Hormozi style"
    )
    sub = parser.add_subparsers(dest="command")

    # check-deps
    deps_parser = sub.add_parser("check-deps", help="Check dependencies")
    deps_parser.add_argument("--install", action="store_true",
                              help="Auto-install missing deps")

    # generate-sfx
    sub.add_parser("generate-sfx", help="Generate synthetic SFX files")

    # edit (default)
    edit_parser = sub.add_parser("edit", help="Edit a video")
    edit_parser.add_argument("--input", "-i", required=True,
                              help="Path to raw footage")
    edit_parser.add_argument("--type", "-t", choices=["reel", "youtube"],
                              required=True, help="Content type")
    edit_parser.add_argument("--style", "-s", default="hormozi",
                              help="Editing style (default: hormozi)")
    edit_parser.add_argument("--captions", default="on",
                              choices=["on", "off"], help="Captions on/off")
    edit_parser.add_argument("--music", "-m", default=None,
                              help="Background music file path")
    edit_parser.add_argument("--broll", "-b", default=None,
                              help="Directory of B-roll files")
    edit_parser.add_argument("--no-zoom", action="store_true",
                              help="Skip punch-in zooms")
    edit_parser.add_argument("--whisper-model", default="base",
                              choices=["tiny", "base", "small", "medium"],
                              help="Whisper model size (default: base)")

    # Also support flat args (no subcommand) for convenience
    parser.add_argument("--input", "-i", default=None)
    parser.add_argument("--type", "-t", choices=["reel", "youtube"], default=None)
    parser.add_argument("--style", "-s", default="hormozi")
    parser.add_argument("--captions", default="on", choices=["on", "off"])
    parser.add_argument("--music", "-m", default=None)
    parser.add_argument("--broll", "-b", default=None)
    parser.add_argument("--no-zoom", action="store_true", default=False)
    parser.add_argument("--whisper-model", default="base",
                         choices=["tiny", "base", "small", "medium"])

    args = parser.parse_args()

    if args.command == "check-deps":
        print("Checking dependencies...")
        ok = check_deps(install=args.install)
        sys.exit(0 if ok else 1)
    elif args.command == "generate-sfx":
        print("Generating synthetic SFX...")
        generate_sfx()
    elif args.command == "edit":
        run_pipeline(args)
    elif args.input and args.type:
        # Flat args mode
        run_pipeline(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
