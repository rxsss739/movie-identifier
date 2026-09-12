from contextlib import contextmanager

import pyfiglet
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

_THEME = Theme(
    {
        "banner":      "bold yellow",
        "success":     "bold green",
        "error":       "bold red",
        "warn":        "bold yellow",
        "info":        "dim white",
        "label":       "dim white",
        "value":       "white",
        "section":     "bold white",
        "evidence":    "cyan",
        "alt":         "red",
        "detail":      "steel_blue1",
        "conf_high":   "bold green",
        "conf_med":    "bold yellow",
        "conf_low":    "bold red",
    }
)

_SPINNER_STYLE = "yellow"
_BORDER_STYLE  = "yellow"


class UI:
    def __init__(self) -> None:
        self.console = Console(theme=_THEME, highlight=False)

    # ── banner ────────────────────────────────────────────────────────────────

    def print_banner(self) -> None:
        try:
            line1 = pyfiglet.figlet_format("MOVIE", font="slant").rstrip()
            line2 = pyfiglet.figlet_format("IDENTIFIER", font="slant").rstrip()
        except Exception:
            line1 = "  MOVIE"
            line2 = "  IDENTIFIER"

        art = Text(justify="center")
        art.append(line1 + "\n", style="bold yellow")
        art.append(line2 + "\n", style="bold yellow")
        art.append(
            "\n  AI-powered movie, TV, and image detection via Gemini Vision  |  v1.1\n",
            style="dim white",
        )

        self.console.print()
        self.console.print(
            Panel(
                Align(art, align="center"),
                border_style=_BORDER_STYLE,
                box=box.ASCII,
                padding=(0, 4),
            )
        )
        self.console.print()

    # ── spinners / status ─────────────────────────────────────────────────────

    @contextmanager
    def spinner(self, message: str):
        with self.console.status(
            f"[bold yellow]{message}",
            spinner="dots",
            spinner_style=_SPINNER_STYLE,
        ):
            yield

    # ── inline messages ───────────────────────────────────────────────────────

    def print_success(self, message: str) -> None:
        self.console.print(f"  [bold green][OK][/bold green]  [white]{message}[/white]")

    def print_error(self, message: str) -> None:
        self.console.print(f"  [bold red][ERROR][/bold red]  [white]{message}[/white]")

    def print_warn(self, message: str) -> None:
        self.console.print(f"  [bold yellow][WARN][/bold yellow]  [white]{message}[/white]")

    def print_info(self, message: str) -> None:
        self.console.print(f"  [dim][INFO] {message}[/dim]")

    # ── result panel ──────────────────────────────────────────────────────────

    def print_result(self, result: dict) -> None:
        self.console.print()
        self.console.print(
            Panel(
                self.build_result_text(result),
                border_style=_BORDER_STYLE,
                box=box.ASCII,
                title="[bold yellow]MOVIE IDENTIFIER[/bold yellow]",
                title_align="center",
                padding=(0, 1),
            )
        )
        self.console.print()

    def build_result_text(self, result: dict) -> Text:
        analysis = result.get("analysis", {})
        top      = analysis.get("top_pick", {})
        evidence = analysis.get("evidence", [])
        alts     = analysis.get("other_possibilities", [])
        details  = analysis.get("visual_details", {})

        confidence = top.get("confidence_percent", 0)
        conf_label = top.get("confidence_label", "")
        media_type = analysis.get("media_type", "movie")

        # confidence colour
        if confidence >= 76:
            conf_style = "conf_high"
        elif confidence >= 51:
            conf_style = "conf_med"
        else:
            conf_style = "conf_low"

        # confidence bar
        filled   = int(confidence / 100 * 22)
        conf_bar = "#" * filled + "-" * (22 - filled)

        type_label = {"tv_show": "TV Show"}.get(media_type, media_type.replace("_", " ").title())

        # ── build Text object ──────────────────────────────────────────────
        t = Text()

        # TOP PICK
        t.append("\n  TOP PICK\n\n", style="bold yellow")

        self._row(t, "Title",      top.get("title", "Unknown"), "bold white")
        self._row(t, "Year",       str(top.get("year") or "Unknown"))
        self._row(t, "Type",       type_label)
        if media_type == "tv_show":
            season = top.get("season")
            episode = top.get("episode")
            episode_title = top.get("episode_title")
            if season:
                self._row(t, "Season", str(season))
            if episode:
                self._row(t, "Episode", str(episode))
            if episode_title:
                self._row(t, "Ep Title", str(episode_title))

        # confidence with inline bar
        t.append("  ")
        t.append(_pad("Confidence"), style="label")
        t.append(conf_bar, style=conf_style)
        t.append(f"  {confidence}%  ", style=conf_style)
        t.append(conf_label + "\n", style="dim white")

        # flags
        if analysis.get("is_multi_source"):
            self._row(t, "Note", "Multi-source - compilation or fan edit", "yellow")
        if analysis.get("is_screen_capture"):
            self._row(t, "Note", "Screen-capture detected", "yellow")
        if analysis.get("quality_issue"):
            self._row(t, "Quality", analysis["quality_issue"], "red")

        # EVIDENCE
        if evidence:
            t.append("\n  -- ", style="dim")
            t.append("EVIDENCE", style="bold cyan")
            t.append(" " + "-" * 42 + "\n\n", style="dim")
            for item in evidence:
                t.append("  - ", style="bold cyan")
                t.append(item + "\n", style="white")

        # ALTERNATIVES
        if alts:
            t.append("\n  -- ", style="dim")
            t.append("ALTERNATIVES", style="bold red")
            t.append(" " + "-" * 39 + "\n\n", style="dim")
            for alt in alts:
                title  = alt.get("title", "")
                year   = alt.get("year", "?")
                pct    = alt.get("confidence_percent", 0)
                notes  = alt.get("notes", "")
                t.append("  - ", style="bold red")
                t.append(f"{title} ({year})", style="white")
                t.append(f"  -  {pct}%\n", style="dim white")
                if notes:
                    t.append(f"      {notes}\n", style="dim")

        # VISUAL DETAILS
        if details:
            t.append("\n  -- ", style="dim")
            t.append("VISUAL DETAILS", style="bold steel_blue1")
            t.append(" " + "-" * 37 + "\n\n", style="dim")
            if details.get("setting"):
                self._row(t, "Setting",    details["setting"])
            if details.get("era"):
                self._row(t, "Era",        details["era"])
            if details.get("color_grade"):
                self._row(t, "Color Grade", details["color_grade"])
            actors = details.get("notable_actors_identified", [])
            if actors:
                self._row(t, "Actors",     ", ".join(actors))
            fmt = details.get("video_format", "")
            if fmt:
                self._row(t, "Format",     fmt.title())
            self._row(t, "Watermark",  "Yes" if details.get("has_watermark") else "No")
            self._row(t, "Subtitles",  "Yes" if details.get("has_subtitles") else "No")

        t.append("\n")

        return t

    def result_plain_text(self, result: dict) -> str:
        return self.build_result_text(result).plain

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _row(t: Text, label: str, value: str, value_style: str = "white") -> None:
        t.append("  ")
        t.append(_pad(label), style="label")
        t.append(value + "\n", style=value_style)


def _pad(label: str, width: int = 14) -> str:
    return label.ljust(width)
