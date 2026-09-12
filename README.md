# Movie Identifier

<img width="956" height="361" alt="image" src="https://github.com/user-attachments/assets/50737191-fbf4-4b54-8c6c-9395ca0c9f20" />

AI-powered CLI tool for identifying movies and TV shows from videos, images, or direct clip links using Gemini Vision.

Drop in a clip, screenshot, or media URL, and Movie Identifier extracts visual clues, asks Gemini Vision what it thinks, then gives you a clean result with title, year, confidence, evidence, alternatives, and TV episode guesses when possible.

## Features

- Identify movies from video files
- Identify TV shows, with season and episode guesses when possible
- Identify from images and screenshots
- Use direct clip links like `https://example.com/movieclip.mp4`
- Interactive prompt when double-clicked with no arguments
- Auto-creates `.env` if missing
- Optional custom `ffmpeg.exe` path through `.env`
- Falls back to bundled ffmpeg or system PATH
- ASCII-safe terminal output
- Save identified results as reusable `.bat` and `.json` files

## Download

Get the latest Windows release from the [Releases page](../../releases).

## Supported Inputs

Videos:

```text
.mp4 .mov .avi .mkv .webm .m4v .flv
```

Images:

```text
.jpg .jpeg .png .webp .bmp
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
FFMPEG_PATH=
```

Get a Gemini API key here:

```text
https://aistudio.google.com/app/apikey
```

`FFMPEG_PATH` is optional. You can set it to either the folder containing `ffmpeg.exe` and `ffprobe.exe`, or directly to `ffmpeg.exe`.

If it is blank or invalid, the app will try to find ffmpeg automatically.

## Usage

Identify a video:

```bash
python main.py "clip.mp4"
```

Identify an image:

```bash
python main.py "screenshot.png"
```

Identify a direct media link:

```bash
python main.py "https://example.com/movieclip.mp4"
```

Use more frames for harder clips:

```bash
python main.py "clip.mp4" --frames 16
```

Print raw JSON:

```bash
python main.py "clip.mp4" --json
```

Save the result:

```bash
python main.py "clip.mp4" --save
```

Saved results go into:

```text
saved-movies/
```

Each saved movie gets its own `.json` file and `.bat` file. Running the `.bat` shows the result again in the terminal.

## Example Output

```text
+--------------------------- MOVIE IDENTIFIER ---------------------------+
|                                                                        |
|   TOP PICK                                                             |
|                                                                        |
|   Title         Toy Story                                              |
|   Year          1995                                                   |
|   Type          Movie                                                  |
|   Confidence    ######################  100%  Certain                  |
|                                                                        |
|   -- EVIDENCE ------------------------------------------               |
|                                                                        |
|   - Bright 3D animated toy characters                                  |
|   - Bedroom setting with childlike objects                             |
|   - Visual style matches early Pixar animation                         |
|                                                                        |
+------------------------------------------------------------------------+
```

## Building an EXE

You can package the app with PyInstaller:

```bash
pyinstaller movie-identifier.spec
```

When running as an `.exe`, the app looks for `.env`, `ffmpeg.exe`, and `ffprobe.exe` next to the executable.

## CLI Options

The `.exe` supports the same commands as the Python version:

```powershell
.\movie-identifier.exe "clip.mp4" --save
.\movie-identifier.exe "clip.mp4" --json
.\movie-identifier.exe --help

## Notes

Movie Identifier works best with clear clips, recognizable characters, scenes, titles, or visual style. Short, blurry, cropped, or heavily edited clips may produce lower-confidence guesses.

## License

MIT License
