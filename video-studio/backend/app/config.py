"""Configuration and constraints for AI News Video Agent Pro."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    groq_api_key: str = ""
    elevenlabs_api_key: str = ""
    pexels_api_key: str = ""
    redis_url: str = "redis://redis:6379/0"

    output_dir: str = "/app/output"
    tmp_dir: str = "/app/tmp"
    font_dir: str = "/app/fonts"

    class Config:
        env_file = ".env"


settings = Settings()

# ─── Video Constraints ───────────────────────────────────────────────
VIDEO_MIN_DURATION = 60
VIDEO_MAX_DURATION = 120
ASPECT_RATIO = "16:9"
RESOLUTION = (1920, 1080)
WIDTH, HEIGHT = RESOLUTION
FPS = 30

# ─── Visual Quality ──────────────────────────────────────────────────
MIN_SCENE_CHANGES = 5
MAX_STATIC_DURATION = 4.0
MUST_INCLUDE_VISUAL = ["motion", "text_overlay"]

# ─── Audio Quality ───────────────────────────────────────────────────
MIN_WPM = 130
MAX_WPM = 170
MAX_SILENCE_GAP = 1.0

# ─── Content Quality ─────────────────────────────────────────────────
NO_HALLUCINATION = True
MUST_MATCH_SOURCE = True

# ─── Engagement ──────────────────────────────────────────────────────
HOOK_WITHIN_SECONDS = 5
MUST_INCLUDE_CTA = True
MUST_INCLUDE_TRANSITIONS = True

# ─── Script Constraints ──────────────────────────────────────────────
MAX_SENTENCE_WORDS = 15
TRANSITION_INTERVAL_SEC = 15

# ─── Visual Plan Constraints ─────────────────────────────────────────
MOTION_TYPES = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "ken_burns"]
TRANSITION_TYPES = ["crossfade", "slide_left", "fade_black"]

# ─── Data Viz Constraints ────────────────────────────────────────────
MAX_CHART_ANIMATION_DURATION = 6.0
CHART_TYPES = ["bar", "line", "pie", "stat_highlight"]

# ─── Voice Constraints ───────────────────────────────────────────────
MAX_PAUSE_BETWEEN_SEGMENTS = 0.5
ELEVENLABS_MODEL = "eleven_multilingual_v2"
ELEVENLABS_VOICE_ID = "pMsXgVXv3BLzUgSXRplE"  # "Serena" - professional news voice

# ─── Composer Constraints ────────────────────────────────────────────
MAX_AV_SYNC_ERROR_MS = 200
CROSSFADE_DURATION = 0.5
TEXT_READ_TIME = 2.0

# ─── QA Constraints ──────────────────────────────────────────────────
QA_MINIMUM_SCORE = 0.9
SCORING_WEIGHTS = {
    "factual_accuracy": 0.35,
    "visual_alignment": 0.25,
    "engagement": 0.20,
    "audio_quality": 0.10,
    "pacing": 0.10,
}
HARD_FAIL_CONDITIONS = [
    "hallucinated_facts",
    "missing_hook",
    "visual_mismatch",
    "audio_silence_gt_2s",
    "static_screen_gt_5s",
]

# ─── Reflection ──────────────────────────────────────────────────────
MAX_REFLECTION_ITERATIONS = 3
REPAIR_STRATEGIES = {
    "low_engagement": "rewrite_hook_and_transitions",
    "visual_mismatch": "regenerate_visual_plan",
    "bad_pacing": "adjust_script_length",
    "low_audio_quality": "regenerate_voice",
}

# ─── Aesthetic Rules ─────────────────────────────────────────────────
COLOR_PALETTE = {
    "bg_dark": "#1A1A1A",
    "bg_light": "#E5E7EB",
    "et_red": "#B90000",
    "et_black": "#000000",
    "et_gray": "#333333",
    "bg_card": "#FFFFFF",
    "accent_blue": "#3B82F6",
    "accent_red": "#B90000",
    "accent_cyan": "#06B6D4",
    "text_white": "#FFFFFF",
    "text_black": "#000000",
    "text_gray": "#4B5563",
    "gradient_start": "#F3F4F6",
    "gradient_end": "#D1D5DB",
    "ticker_bg": "#1A1A1A",
    "ticker_red": "#B90000",
    "ticker_text": "#FFFFFF",
    "overlay_bg": "rgba(255,255,255,0.9)",
}
FONT_BOLD = "Montserrat-Bold"
FONT_EXTRABOLD = "Montserrat-ExtraBold"
FONT_SEMIBOLD = "Montserrat-SemiBold"
