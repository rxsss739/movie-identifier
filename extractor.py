import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def get_video_duration(video_path: Path, ffprobe_bin: str = "ffprobe") -> float:
    try:
        result = subprocess.run(
            [
                ffprobe_bin, "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return float(result.stdout.strip())
    except Exception:
        return 30.0  # safe default


def calculate_frame_count(duration: float) -> int:
    if duration <= 15:
        return 4
    elif duration <= 30:
        return 6
    elif duration <= 60:
        return 8
    elif duration <= 120:
        return 12
    return 16


def extract_frames(
    video_path: Path,
    num_frames: int,
    ui,
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
) -> tuple[list[str], Path]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="movie-id-"))

    duration = get_video_duration(video_path, ffprobe_bin)

    # Use smart count only if user left the default (8)
    if num_frames == 8:
        num_frames = calculate_frame_count(duration)

    with ui.spinner(f"Extracting frames from {round(duration, 1)}s video..."):
        # Try scene-based extraction first
        scene_ok = _scene_extraction(video_path, tmp_dir, ffmpeg_bin)
        frames_found = list(tmp_dir.glob("*.jpg"))

        # Fall back to time-based if scene gave too few frames
        if not scene_ok or len(frames_found) < 2:
            _clear_dir(tmp_dir)
            _time_extraction(video_path, tmp_dir, num_frames, ffmpeg_bin)

    frames = sorted(tmp_dir.glob("*.jpg"))

    if not frames:
        ui.print_error("No frames could be extracted — check that ffmpeg is installed and the video is not corrupt.")
        return [], tmp_dir

    ui.print_success(f"Extracted {len(frames)} frames")
    return [str(f) for f in frames], tmp_dir


def prepare_image_frame(image_path: Path, ui) -> tuple[list[str], Path]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="movie-id-"))
    output_path = tmp_dir / "image_01.jpg"

    with ui.spinner("Preparing image..."):
        try:
            with Image.open(image_path) as image:
                image.thumbnail((1280, 1280))
                image.convert("RGB").save(output_path, "JPEG", quality=90)
        except Exception as e:
            ui.print_error(f"Image could not be opened: {e}")
            return [], tmp_dir

    ui.print_success("Prepared image")
    return [str(output_path)], tmp_dir


# ── private helpers ──────────────────────────────────────────────────────────

def _scene_extraction(video_path: Path, tmp_dir: Path, ffmpeg_bin: str) -> bool:
    try:
        result = subprocess.run(
            [
                ffmpeg_bin, "-i", str(video_path),
                "-vf", "select='gt(scene,0.3)',scale=640:-1",
                "-vsync", "vfr",
                str(tmp_dir / "frame_%02d.jpg"),
                "-y",
            ],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


def _time_extraction(video_path: Path, tmp_dir: Path, num_frames: int, ffmpeg_bin: str) -> bool:
    try:
        result = subprocess.run(
            [
                ffmpeg_bin, "-i", str(video_path),
                "-vf", "fps=1,scale=640:-1",
                "-frames:v", str(num_frames),
                str(tmp_dir / "frame_%02d.jpg"),
                "-y",
            ],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


def _clear_dir(directory: Path) -> None:
    for f in directory.glob("*.jpg"):
        f.unlink(missing_ok=True)
