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

# Максимум символов за одну озвучку (бесплатный тариф ElevenLabs — 10 000 символов в месяц)
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
# Длинный текст режется по предложениям на части такого размера и склеивается в один mp3
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
# Максимальный размер .txt-файла с инструкцией
MAX_FILE_SIZE = 100_000

AUDIO_DIR = Path(os.getenv("AUDIO_DIR", BASE_DIR / "audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
# Выбранные пользователями голос и режим — переживают перезапуск бота
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"

# Стандартные женские голоса ElevenLabs — доступны по API на бесплатном тарифе.
# Чтобы добавить голос: скопируйте его Voice ID в кабинете ElevenLabs и допишите строку.
VOICES = {
    "EXAVITQu4vr4xnSDxMaL": ("Sarah", "мягкий, спокойный — для медитаций"),
    "XrExE9yKIg1WjnnlVkGX": ("Matilda", "деловой, грамотный — для обучающих текстов"),
    "Xb7hH8MSUJpSbSDYk0k2": ("Alice", "уверенный, чёткий — для инструкций"),
    "FGY2WhTYpPnrIDTdsKH5": ("Laura", "живой, энергичный — для анонсов"),
    "pFZP5JQG7iQjIQuC4Bku": ("Lily", "бархатный, неспешный — для сказок"),
}
DEFAULT_VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"

# Сценарии озвучки. При выборе режима ставится его голос, темп и пауза между пунктами.
#   step_word — как читать нумерованный пункт «1.»: «Шаг 1.», «Пункт 1.»
#   pause     — пауза после каждого пункта списка, секунд
#   speed     — темп речи ElevenLabs (0.7 — медленно, 1.0 — обычно, 1.2 — быстро)
#   stability — ровность интонации (выше — ровнее и спокойнее, ниже — живее)
MODES = {
    "instruction": {
        "title": "📋 Инструкция",
        "desc": "чётко и чуть медленнее, «Шаг 1, Шаг 2», паузы между шагами — чтобы успеть сделать",
        "voice": "Xb7hH8MSUJpSbSDYk0k2",
        "step_word": "Шаг",
        "pause": 1.0,
        "speed": 0.92,
        "stability": 0.6,
    },
    "training": {
        "title": "🎓 Обучение",
        "desc": "спокойный лекционный темп для уроков и регламентов",
        "voice": "XrExE9yKIg1WjnnlVkGX",
        "step_word": "Пункт",
        "pause": 0.6,
        "speed": 1.0,
        "stability": 0.5,
    },
    "memo": {
        "title": "📌 Памятка",
        "desc": "коротко и бодро, короткие паузы — прослушать на ходу",
        "voice": "FGY2WhTYpPnrIDTdsKH5",
        "step_word": "Пункт",
        "pause": 0.4,
        "speed": 1.08,
        "stability": 0.45,
    },
}
DEFAULT_MODE = "instruction"
