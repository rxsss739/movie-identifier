import json
import os
from pathlib import Path

import PIL.Image
from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are a movie identification assistant. Your job is to analyze video frames and identify what movie or TV show is being shown.

You will ALWAYS respond with valid JSON only. No prose, no markdown, no backticks, no explanation outside the JSON. Your entire response must be parseable by json.loads().

Always use this exact schema:
{
  "analysis": {
    "media_type": "movie" | "tv_show" | "unknown",
    "is_multi_source": boolean,
    "is_screen_capture": boolean,
    "quality_issue": string | null,
    "top_pick": {
      "title": string,
      "year": number | null,
      "season": number | null,
      "episode": number | null,
      "episode_title": string | null,
      "confidence_percent": number,
      "confidence_label": string
    },
    "evidence": [string],
    "other_possibilities": [
      {
        "title": string,
        "year": number | null,
        "confidence_percent": number,
        "notes": string
      }
    ],
    "sources": [],
    "visual_details": {
      "setting": string,
      "color_grade": string,
      "era": string,
      "notable_actors_identified": [string],
      "video_format": "landscape" | "vertical" | "square",
      "has_watermark": boolean,
      "has_subtitles": boolean
    }
  }
}

Rules:
- evidence: 3–6 specific visual clues that led to the identification
- other_possibilities: 2–4 alternatives ordered by likelihood; empty array [] if none
- confidence_label: 0–25 = "Low", 26–50 = "Medium", 51–75 = "High", 76–90 = "Very High", 91–100 = "Certain"
- If media_type is "tv_show", still fill in top_pick with the show name and premiere year. Guess season, episode, and episode_title when there are enough clues; otherwise use null.
- If video appears to be a compilation or fan edit, set is_multi_source to true
- If a screen is visible playing something inside the video, set is_screen_capture to true
- If quality is too poor to identify, set top_pick title to "Unknown", year to null, and explain in quality_issue
- Never break the JSON schema under any circumstances"""


def identify_movie(frame_paths: list[str], ui) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")

    client = genai.Client(api_key=api_key)

    images = [PIL.Image.open(fp) for fp in frame_paths]
    prompt = "Analyze these frames or images and identify the movie or TV show."

    try:
        raw = _ask_gemini(client, images, prompt, ui)
        try:
            return _parse_json(raw)
        except json.JSONDecodeError:
            retry_prompt = (
                "Your previous answer was not valid JSON. Return the same analysis again "
                "as one complete JSON object only. Do not include markdown or prose."
            )
            raw = _ask_gemini(client, images, retry_prompt, ui, retry=True)
            return _parse_json(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}\n\nRaw response:\n{raw}")
    finally:
        for image in images:
            image.close()


def _ask_gemini(client, images: list[PIL.Image.Image], prompt: str, ui, retry: bool = False) -> str:
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=4096,
        temperature=0.1,
        response_mime_type="application/json",
    )

    message = images + [prompt]
    status = "Retrying Gemini with stricter JSON..." if retry else "Consulting Gemini Vision..."

    with ui.spinner(status):
        chat = client.chats.create(model="gemini-3.6-flash", config=config)
        response = chat.send_message(message)

    raw = response.text.strip()
    return raw


def _parse_json(raw: str) -> dict:
    # Strip markdown fences if model misbehaves
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)
