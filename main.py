import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import typer
from dotenv import load_dotenv

from extractor import extract_frames, prepare_image_frame
from identifier import identify_movie
from ui import UI
from utils import cleanup_frames, detect_os, is_image, is_video, resolve_ffmpeg, validate_file

# ── resolve the directory that holds the exe (or the script) ─────────────────
if getattr(sys, "frozen", False):
    # Running as a PyInstaller exe — .env lives next to the .exe
    _BASE_DIR = Path(sys.executable).parent
else:
    # Running as a plain script
    _BASE_DIR = Path(__file__).parent

_ENV_FILE = _BASE_DIR / ".env"
_ENV_TEMPLATE = "GEMINI_API_KEY=your_api_key_here\nFFMPEG_PATH=\n"

# ── .env bootstrap ────────────────────────────────────────────────────────────
def _bootstrap_env(ui: UI) -> bool:
    """
    Returns True if .env is present and has a real key.
    Returns False (and handles messaging) if the user still needs to set it up.
    """
    if not _ENV_FILE.exists():
        _ENV_FILE.write_text(_ENV_TEMPLATE, encoding="utf-8")
        ui.print_banner()
        ui.console.print()
        ui.print_warn(".env file not found — created one for you.")
        ui.console.print()
        ui.console.print(
            f"  [dim]Open[/dim] [bold white]{_ENV_FILE}[/bold white] "
            "[dim]and replace[/dim] [yellow]your_api_key_here[/yellow] "
            "[dim]with your Gemini API key, then run the app again.[/dim]"
        )
        ui.console.print()
        ui.console.print(
            "  [dim]Get a free key at:[/dim] "
            "[bold cyan]https://aistudio.google.com/app/apikey[/bold cyan]"
        )
        ui.console.print()
        _pause()
        return False

    env_text = _ENV_FILE.read_text(encoding="utf-8", errors="ignore")
    if "FFMPEG_PATH=" not in env_text:
        with open(_ENV_FILE, "a", encoding="utf-8") as f:
            if env_text and not env_text.endswith("\n"):
                f.write("\n")
            f.write("FFMPEG_PATH=\n")

    load_dotenv(_ENV_FILE)

    key = os.getenv("GEMINI_API_KEY", "")
    if not key or key == "your_api_key_here":
        ui.print_banner()
        ui.console.print()
        ui.print_warn("GEMINI_API_KEY is not set in your .env file.")
        ui.console.print()
        ui.console.print(
            f"  [dim]Open[/dim] [bold white]{_ENV_FILE}[/bold white] "
            "[dim]and replace[/dim] [yellow]your_api_key_here[/yellow] "
            "[dim]with your real Gemini API key, then run the app again.[/dim]"
        )
        ui.console.print()
        ui.console.print(
            "  [dim]Get a free key at:[/dim] "
            "[bold cyan]https://aistudio.google.com/app/apikey[/bold cyan]"
        )
        ui.console.print()
        _pause()
        return False

    return True


def _pause() -> None:
    """Keep the window open when double-clicked on Windows."""
    if getattr(sys, "frozen", False):
        input("  Press Enter to exit...")


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _download_media(url: str, ui: UI) -> tuple[Path | None, Path | None]:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name or "downloaded-clip.mp4"
    suffix = Path(name).suffix.lower() or ".mp4"
    tmp_dir = Path(tempfile.mkdtemp(prefix="movie-id-download-"))
    output_path = tmp_dir / f"downloaded{suffix}"

    try:
        with ui.spinner("Downloading media link..."):
            request = Request(url, headers={"User-Agent": "movie-identifier/1.1"})
            with urlopen(request, timeout=60) as response:
                with open(output_path, "wb") as f:
                    shutil.copyfileobj(response, f)
    except Exception as e:
        cleanup_frames(tmp_dir)
        ui.print_error(f"Could not download media link: {e}")
        return None, None

    ui.print_success(f"Downloaded media link: {name}")
    return output_path, tmp_dir


# ── CLI ───────────────────────────────────────────────────────────────────────
app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
ui  = UI()


@app.command()
def identify(
    media: Optional[str] = typer.Argument(
        None, help="Path or direct http(s) link to a video or image"
    ),
    frames: int = typer.Option(
        8, "--frames", "-f",
        help="Number of frames to extract (default: auto based on video length)",
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Print raw JSON output instead of the visual result",
    ),
    save: bool = typer.Option(
        False, "--save", "-s",
        help="Save result in the saved-movies folder",
    ),
) -> None:

    # .env check first — exits early if not configured
    if not _bootstrap_env(ui):
        raise typer.Exit(0)

    ui.print_banner()

    # OS detection
    os_name = detect_os()
    ui.print_info(f"OS detected: {os_name}")

    # If no media was passed (double-click), prompt interactively
    if media is None:
        ui.console.print()
        ui.print_info("Tip: you can also run  movie-identifier <video_or_image>  directly.")
        ui.console.print()
        media = typer.prompt("  Drop/type a video, image, or direct media link")
        media = media.strip().strip('"').strip("'")   # handle drag-and-drop quotes

    download_dir: Path | None = None
    if _is_url(media):
        media_path, download_dir = _download_media(media, ui)
        if media_path is None:
            _pause()
            raise typer.Exit(1)
        display_name = media
    else:
        media_path = Path(media)
        display_name = media_path.name

    # File validation
    error = validate_file(media_path)
    if error:
        ui.print_error(error)
        cleanup_frames(download_dir)
        _pause()
        raise typer.Exit(1)

    ui.print_success(f"File validated: {display_name}")
    ui.console.print()

    ffmpeg_bin = None
    ffprobe_bin = None
    if is_video(media_path):
        ffmpeg_bin, ffprobe_bin, ffmpeg_warning = resolve_ffmpeg(os.getenv("FFMPEG_PATH"), _BASE_DIR)
        if ffmpeg_warning:
            ui.print_warn(ffmpeg_warning)
        if not ffmpeg_bin or not ffprobe_bin:
            ui.print_error(
                "ffmpeg / ffprobe not found. Add FFMPEG_PATH to .env, put ffmpeg.exe next to the app, or install ffmpeg in PATH."
            )
            cleanup_frames(download_dir)
            _pause()
            raise typer.Exit(1)

    # Frame/image preparation
    if is_video(media_path):
        frame_paths, tmp_dir = extract_frames(media_path, frames, ui, ffmpeg_bin, ffprobe_bin)
    elif is_image(media_path):
        frame_paths, tmp_dir = prepare_image_frame(media_path, ui)
    else:
        ui.print_error("Unsupported media type.")
        cleanup_frames(download_dir)
        _pause()
        raise typer.Exit(1)

    if not frame_paths:
        cleanup_frames(tmp_dir)
        cleanup_frames(download_dir)
        _pause()
        raise typer.Exit(1)

    # Identification
    try:
        result = identify_movie(frame_paths, ui)
    except ValueError as e:
        ui.print_error(str(e))
        cleanup_frames(tmp_dir)
        cleanup_frames(download_dir)
        _pause()
        raise typer.Exit(1)
    except Exception as e:
        ui.print_error(f"Unexpected error from Gemini: {e}")
        cleanup_frames(tmp_dir)
        cleanup_frames(download_dir)
        _pause()
        raise typer.Exit(1)
    finally:
        cleanup_frames(tmp_dir)
        cleanup_frames(download_dir)

    ui.console.print()

    # Output
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        ui.print_result(result)

    # Save
    if save:
        saved_paths = _save_result(result, display_name, os_name, len(frame_paths), ui)
        ui.print_success(f"Saved movie files: {saved_paths[0].parent}")

    ui.console.print()
    _pause()


def _save_result(result: dict, filename: str, os_name: str, frame_count: int, ui: UI) -> tuple[Path, Path]:
    entry = {
        "file":        filename,
        "timestamp":   datetime.now().isoformat(),
        "os":          os_name,
        "frames_used": frame_count,
        "result":      result,
    }

    saved_dir = _BASE_DIR / "saved-movies"
    saved_dir.mkdir(exist_ok=True)

    analysis = result.get("analysis", {})
    top = analysis.get("top_pick", {})
    title = str(top.get("title") or "unknown")
    year = str(top.get("year") or "unknown")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = _safe_filename(f"{title}-{year}-{timestamp}")

    json_path = saved_dir / f"{stem}.json"
    bat_path = saved_dir / f"{stem}.bat"

    json_path.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_result_bat(bat_path, result, ui)
    return bat_path, json_path


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "movie-result"


def _write_result_bat(path: Path, result: dict, ui: UI) -> None:
    lines = [
        "@echo off",
        "title Movie Identifier Result",
        "cls",
    ]

    display_lines = _saved_display(result, ui).splitlines()
    for line in display_lines:
        if not line:
            lines.append("echo(")
        else:
            lines.append(f"echo({_escape_bat_echo(line)}")

    lines.extend(["echo(", "pause"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _saved_display(result: dict, ui: UI) -> str:
    body = ui.result_plain_text(result).strip("\n")
    width = max(72, min(118, max((len(line) for line in body.splitlines()), default=72) + 4))
    title = " MOVIE IDENTIFIER "
    left = (width - len(title)) // 2
    right = width - len(title) - left
    border = "+" + "-" * left + title + "-" * right + "+"
    blank = "|" + " " * width + "|"

    output = [border, blank]
    for line in body.splitlines():
        output.append("| " + line.ljust(width - 2) + " |")
    output.extend([blank, "+" + "-" * width + "+"])
    return "\n".join(output)


def _escape_bat_echo(value: str) -> str:
    for char in "^&<>|":
        value = value.replace(char, "^" + char)
    return value


if __name__ == "__main__":
    app()
