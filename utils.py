import platform
import shutil
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS


def detect_os() -> str:
    system = platform.system()
    if system == "Windows":
        try:
            import colorama
            colorama.init(autoreset=True)
        except ImportError:
            pass
    return system


def validate_file(path: Path) -> str | None:
    """Returns an error string if invalid, None if valid."""
    if not path.exists():
        return f"File not found: {path}"
    if not path.is_file():
        return f"Not a file: {path}"
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        return f"Unsupported format '{path.suffix}'. Supported: {supported}"
    return None


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def resolve_ffmpeg(configured_path: str | None, base_dir: Path) -> tuple[str | None, str | None, str | None]:
    """
    Returns ffmpeg path, ffprobe path, and a warning if the configured path was unusable.
    """
    warning = None

    if configured_path:
        configured = Path(configured_path.strip().strip('"').strip("'"))
        if configured.is_dir():
            ffmpeg = configured / "ffmpeg.exe"
            ffprobe = configured / "ffprobe.exe"
        else:
            ffmpeg = configured
            ffprobe = configured.with_name("ffprobe.exe")

        if ffmpeg.exists() and ffprobe.exists():
            return str(ffmpeg), str(ffprobe), None

        warning = f"FFMPEG_PATH in .env is invalid, so I will try to find ffmpeg automatically: {configured}"

    bundled_ffmpeg = base_dir / "ffmpeg.exe"
    bundled_ffprobe = base_dir / "ffprobe.exe"
    if bundled_ffmpeg.exists() and bundled_ffprobe.exists():
        return str(bundled_ffmpeg), str(bundled_ffprobe), warning

    path_ffmpeg = shutil.which("ffmpeg")
    path_ffprobe = shutil.which("ffprobe")
    if path_ffmpeg and path_ffprobe:
        return path_ffmpeg, path_ffprobe, warning

    return None, None, warning


def cleanup_frames(tmp_dir: Path) -> None:
    if tmp_dir and tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
