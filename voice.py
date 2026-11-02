import logging
from datetime import datetime
from pathlib import Path

from elevenlabs.client import AsyncElevenLabs
from elevenlabs.core import ApiError

import config

log = logging.getLogger(__name__)

client = AsyncElevenLabs(api_key=config.ELEVENLABS_API_KEY)


class VoiceError(Exception):
    """Ошибка озвучки с текстом, который можно показать пользователю."""


def _user_message(err: ApiError) -> str:
    body = str(err.body).lower()
    if "quota" in body:
        return "Закончился лимит символов ElevenLabs на этот месяц."
    if err.status_code == 401:
        return "ElevenLabs отклонил ключ API. Проверьте ELEVENLABS_API_KEY в .env."
    if err.status_code == 429:
        return "ElevenLabs сейчас перегружен. Попробуйте через минуту."
    return "Не удалось озвучить текст. Попробуйте ещё раз позже."


async def synthesize(text: str, voice_id: str) -> Path:
    """Озвучивает текст и сохраняет mp3 в папку audio/. Возвращает путь к файлу."""
    name = config.VOICES[voice_id][0]
    path = config.AUDIO_DIR / f"{datetime.now():%Y-%m-%d_%H%M%S}_{name}.mp3"
    try:
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=config.MODEL_ID,
            output_format=config.OUTPUT_FORMAT,
        )
        with path.open("wb") as f:
            async for chunk in audio:
                f.write(chunk)
    except ApiError as e:
        path.unlink(missing_ok=True)
        log.warning("ElevenLabs error %s: %s", e.status_code, e.body)
        raise VoiceError(_user_message(e)) from e
    except Exception as e:
        path.unlink(missing_ok=True)
        log.exception("Ошибка соединения с ElevenLabs")
        raise VoiceError("Нет связи с ElevenLabs. Попробуйте ещё раз позже.") from e

    log.info("Сохранён файл %s (%d символов)", path.name, len(text))
    return path


async def preview_url(voice_id: str) -> str | None:
    """Ссылка на образец звучания голоса из каталога ElevenLabs."""
    try:
        voice = await client.voices.get(voice_id=voice_id)
    except ApiError as e:
        log.warning("Не удалось получить пример голоса %s: %s", voice_id, e.status_code)
        return None
    return voice.preview_url
