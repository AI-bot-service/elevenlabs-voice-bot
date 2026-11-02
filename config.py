import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ["BOT_TOKEN"]
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]

# eleven_multilingual_v2 — лучшее качество для русского языка
MODEL_ID = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
OUTPUT_FORMAT = "mp3_44100_128"

MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "2500"))

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", BASE_DIR / "audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Стандартные женские голоса ElevenLabs — доступны по API на бесплатном тарифе.
# Чтобы добавить голос: скопируйте его Voice ID в кабинете ElevenLabs и допишите строку.
VOICES = {
    "EXAVITQu4vr4xnSDxMaL": ("Sarah", "мягкий, спокойный — для медитаций"),
    "XrExE9yKIg1WjnnlVkGX": ("Matilda", "деловой, грамотный — для обучающих текстов"),
    "Xb7hH8MSUJpSbSDYk0k2": ("Alice", "уверенный, чёткий — для инструкций"),
    "FGY2WhTYpPnrIDTdsKH5": ("Laura", "живой, энергичный — для анонсов"),
    "pFZP5JQG7iQjIQuC4Bku": ("Lily", "бархатный, неспешный — для сказок"),
}
DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
