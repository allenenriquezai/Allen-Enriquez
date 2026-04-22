# Transcribe SOP (video → word-level JSON)

Use this whenever a reel's beats/timing need to be derived from an existing video (e.g. CapCut raw export, reshot take, reference cut).

## Tool

`tools/transcribe_video.py` — wrapper around ffmpeg + whisper.cpp.

Produces word-level timestamps via whisper-cli `-ojf` (JSON full).

## Dependencies (already installed)

- `ffmpeg` — `brew install ffmpeg`
- `whisper-cli` — `brew install whisper-cpp`
- Model at `~/.cache/hyperframes/whisper/models/ggml-small.en.bin`

## Command

```bash
python3 tools/transcribe_video.py \
  "<path/to/video.mov>" \
  --out ".tmp/videos/<slug>/transcript"
```

Outputs (same prefix):
- `transcript.json` — word-level timings (use this for beat detection)
- `transcript.srt` — subtitle file (quick readable scan)
- `transcript.txt` — plain text
- `transcript.wav` — 16kHz mono PCM (intermediate, safe to delete)

## Defaults

- Model: `ggml-small.en` (good English accuracy, fast on M-series)
- Threads: 8
- Language: English (model is `.en`)
- Segment length: unlimited (`-ml 0`)

## When transcribing for `/scene-animation`

1. Run the tool on the raw .mov.
2. Open the `.srt` to eyeball the spoken timeline.
3. Ask Allen for black-section start/end (he watches the video, reports timestamps).
4. Slice the transcript to that window.
5. Use word-level `.json` to place each item's entrance offset on the spoken cue (e.g. "Number one" → scene 1 entrance at that word's `start`).
6. Every scene's `data-duration` = time from that cue to the next cue's `start`.

## When transcribing for other skills

Same tool. Also valid for:
- `/short-form-video` retime after edits (rerun on new cut, diff against old JSON for word shifts)
- `/content` post-production — pulling quotable lines out of long-form with exact timestamps
- `/call-notes` on recorded calls (use a multilingual model if needed — swap `--model`)

## If you need a bigger/multilingual model

```bash
# download once
curl -L -o ~/.cache/hyperframes/whisper/models/ggml-medium.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin

# use it
python3 tools/transcribe_video.py <input> \
  --model ~/.cache/hyperframes/whisper/models/ggml-medium.bin
```
