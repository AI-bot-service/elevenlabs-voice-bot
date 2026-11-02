import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

from elevenlabs import VoiceSettings
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


def _strip_id3(data: bytes) -> bytes:
    """Убирает ID3-тег в начале mp3: в середине склеенного файла он ломает воспроизведение."""
    if data[:3] != b"ID3":
        return data
    size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
    return data[10 + size :]


async def synthesize(
    parts: list[str],
    voice_id: str,
    mode: str,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> Path:
    """Озвучивает части текста по очереди и склеивает их в один mp3 в папке audio/.

    Соседние части передаются в previous_text / next_text — так ElevenLabs сохраняет
    интонацию на стыках, и склейка не слышна.
    """
    preset = config.MODES[mode]
    settings = VoiceSettings(
        stability=preset["stability"],
        similarity_boost=0.75,
        speed=preset["speed"],
    )
    name = config.VOICES[voice_id][0]
    path = config.AUDIO_DIR / f"{datetime.now():%Y-%m-%d_%H%M%S}_{mode}_{name}.mp3"
    try:
        with path.open("wb") as f:
            for i, part in enumerate(parts):
                if on_progress and len(parts) > 1:
                    await on_progress(i + 1, len(parts))
                audio = client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=part,
                    model_id=config.MODEL_ID,
                    output_format=config.OUTPUT_FORMAT,
                    voice_settings=settings,
                    previous_text=parts[i - 1] if i > 0 else None,
                    next_text=parts[i + 1] if i + 1 < len(parts) else None,
                )
                data = b"".join([chunk async for chunk in audio])
                f.write(data if i == 0 else _strip_id3(data))
    except ApiError as e:
        path.unlink(missing_ok=True)
        log.warning("ElevenLabs error %s: %s", e.status_code, e.body)
        raise VoiceError(_user_message(e)) from e
    except Exception as e:
        path.unlink(missing_ok=True)
        log.exception("Ошибка соединения с ElevenLabs")
        raise VoiceError("Нет связи с ElevenLabs. Попробуйте ещё раз позже.") from e

    log.info("Сохранён файл %s (%d частей)", path.name, len(parts))
    return path


async def preview_url(voice_id: str) -> str | None:
    """Ссылка на образец звучания голоса из каталога ElevenLabs."""
    try:
        voice = await client.voices.get(voice_id=voice_id)
    except ApiError as e:
        log.warning("Не удалось получить пример голоса %s: %s", voice_id, e.status_code)
        return None
    return voice.preview_url


async def quota() -> tuple[int, int] | None:
    """Сколько символов потрачено и сколько доступно в этом месяце.

    Нужно право User → Read у ключа ElevenLabs; без него возвращает None.
    """
    try:
        sub = await client.user.subscription.get()
    except ApiError as e:
        log.warning("Не удалось получить квоту ElevenLabs: %s", e.status_code)
        return None
    return sub.character_count, sub.character_limit
