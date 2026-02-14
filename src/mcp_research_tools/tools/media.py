"""Media processing tool: download, trim, extract frames + audio, transcribe."""

import asyncio
import hashlib
import re
from pathlib import Path

from ..config import FRAME_EVERY_SECONDS, MAX_VIDEO_SECONDS, MEDIA_TEMP_DIR

MEDIA_URL_PATTERNS = [
    re.compile(r"(youtube\.com|youtu\.be)"),
    re.compile(r"tiktok\.com"),
]


def is_media_url(url: str) -> bool:
    """Check if URL matches a supported media platform."""
    return any(p.search(url) for p in MEDIA_URL_PATTERNS)


async def _run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


async def _get_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    rc, out, _ = await _run_cmd([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ])
    if rc != 0:
        return 0.0
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def _find_video_file(work_dir: Path) -> Path | None:
    """Find the downloaded video file in work_dir."""
    for ext in ("mkv", "mp4", "webm", "mov", "avi", "flv"):
        matches = list(work_dir.glob(f"video.{ext}"))
        if matches:
            return matches[0]
    return None


def _list_frames(frames_dir: Path) -> list[str]:
    """List extracted frame file paths, sorted."""
    if not frames_dir.exists():
        return []
    return sorted(str(f) for f in frames_dir.glob("out_*.jpg"))


async def _transcribe(audio_path: Path) -> str:
    """Transcribe audio using whisper-cli. Returns transcript text."""
    from ..config import WHISPER_CPP_BIN, WHISPER_MODEL_PATH

    if not audio_path.exists():
        return ""

    # whisper-cli needs WAV input, convert first
    wav_path = audio_path.with_suffix(".wav")
    rc, _, err = await _run_cmd([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(wav_path),
    ])
    if rc != 0:
        return f"[audio conversion failed: {err}]"

    rc, out, err = await _run_cmd([
        WHISPER_CPP_BIN,
        "-m", WHISPER_MODEL_PATH,
        "-f", str(wav_path),
        "-otxt",
        "-np",
    ])
    if rc != 0:
        return f"[transcription failed: {err}]"

    # Read the .txt output file
    txt_path = wav_path.with_suffix(".wav.txt")
    if txt_path.exists():
        return txt_path.read_text().strip()

    return out.strip()


async def process_media(url: str) -> dict:
    """Download and process a video URL into transcript + keyframes.

    Pipeline:
    1. yt-dlp downloads the video
    2. ffmpeg trims to MAX_VIDEO_SECONDS
    3. ffmpeg extracts audio as MP3
    4. ffmpeg extracts keyframes every FRAME_EVERY_SECONDS
    5. whisper-cli transcribes audio to text

    Returns:
        Dict with transcript, frame paths, audio path, duration, source URL.
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    work_dir = MEDIA_TEMP_DIR / url_hash
    work_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    # 1. Download
    rc, _, err = await _run_cmd([
        "yt-dlp",
        "-f", "bv*+ba/b",
        "-o", str(work_dir / "video.%(ext)s"),
        "--no-playlist",
        url,
    ])
    if rc != 0:
        return {"error": f"Download failed: {err}", "source_url": url}

    video_file = _find_video_file(work_dir)
    if not video_file:
        return {"error": "No video file found after download", "source_url": url}

    # 2. Trim to cap
    duration = await _get_duration(video_file)
    trimmed = work_dir / "trimmed.mkv"

    if duration > MAX_VIDEO_SECONDS:
        rc, _, _ = await _run_cmd([
            "ffmpeg", "-y", "-i", str(video_file),
            "-t", str(MAX_VIDEO_SECONDS), "-c", "copy",
            str(trimmed),
        ])
        if rc != 0:
            await _run_cmd([
                "ffmpeg", "-y", "-i", str(video_file),
                "-t", str(MAX_VIDEO_SECONDS),
                str(trimmed),
            ])
    else:
        trimmed = video_file

    actual_duration = min(duration, MAX_VIDEO_SECONDS)

    # 3. Extract audio
    audio_path = work_dir / "audio.mp3"
    await _run_cmd([
        "ffmpeg", "-y", "-i", str(trimmed),
        "-vn", "-q:a", "4",
        str(audio_path),
    ])

    # 4. Extract keyframes
    await _run_cmd([
        "ffmpeg", "-y", "-i", str(trimmed),
        "-vf", f"fps=1/{FRAME_EVERY_SECONDS}",
        "-q:v", "3",
        str(frames_dir / "out_%04d.jpg"),
    ])

    # 5. Transcribe
    transcript = await _transcribe(audio_path)

    return {
        "transcript": transcript,
        "frames": _list_frames(frames_dir),
        "audio_path": str(audio_path),
        "duration_seconds": actual_duration,
        "source_url": url,
        "work_dir": str(work_dir),
    }
