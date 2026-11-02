import asyncio
import json
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.chat_action import ChatActionSender

import config
import text_prep
import voice

router = Router()

HELP_TEXT = (
    "<b>Что подойдёт для озвучки</b>\n"
    "Инструкции, регламенты, памятки, обучающие тексты — обычным текстом или файлом .txt. "
    "Нумерованные пункты «1.», «2)» я прочитаю как «Шаг 1», «Шаг 2» и сделаю паузу после каждого.\n\n"
    "<b>Перед озвучкой я сам</b>\n"
    "• убираю разметку, эмодзи и ссылки\n"
    "• раскрываю сокращения: т.е., и т.д., см., №, °C\n"
    "• режу длинный текст по предложениям и склеиваю в один mp3\n\n"
    "<b>Чего я не делаю</b>\n"
    "• не редактирую и не сокращаю текст — читаю как есть\n"
    "• не проверяю, правильная ли инструкция\n"
    "• не монтирую аудио: без музыки, эффектов и нескольких голосов\n\n"
    f"<b>Лимиты</b>: до {config.MAX_TEXT_LENGTH} символов за раз, файл .txt до 100 КБ. "
    "Бесплатный тариф ElevenLabs — 10 000 символов в месяц, остаток — /quota."
)

# user_id → {"voice": ..., "mode": ...}
user_settings: dict[str, dict[str, str]] = {}


def load_settings() -> None:
    if config.SETTINGS_FILE.exists():
        user_settings.update(json.loads(config.SETTINGS_FILE.read_text(encoding="utf-8")))


def save_settings() -> None:
    config.SETTINGS_FILE.parent.mkdir(exist_ok=True)
    config.SETTINGS_FILE.write_text(json.dumps(user_settings, ensure_ascii=False, indent=1), encoding="utf-8")


def get_settings(user_id: int) -> tuple[str, str]:
    s = user_settings.get(str(user_id), {})
    mode = s.get("mode") if s.get("mode") in config.MODES else config.DEFAULT_MODE
    voice_id = s.get("voice") if s.get("voice") in config.VOICES else config.MODES[mode]["voice"]
    return mode, voice_id


def update_settings(user_id: int, **values: str) -> None:
    user_settings.setdefault(str(user_id), {}).update(values)
    save_settings()


def modes_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=m["title"], callback_data=f"mode:{key}")] for key, m in config.MODES.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def voices_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=f"🎙 {name}", callback_data=f"voice:{vid}"),
            InlineKeyboardButton(text="▶️ пример", callback_data=f"preview:{vid}"),
        ]
        for vid, (name, _) in config.VOICES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def modes_list() -> str:
    return "\n".join(f"<b>{m['title']}</b> — {m['desc']}" for m in config.MODES.values())


def voices_list() -> str:
    return "\n".join(f"<b>{name}</b> — {desc}" for name, desc in config.VOICES.values())


def current_line(user_id: int) -> str:
    mode, voice_id = get_settings(user_id)
    return f"Сейчас: {config.MODES[mode]['title']}, голос <b>{config.VOICES[voice_id][0]}</b>"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я превращаю текстовые инструкции в аудиофайлы mp3 — "
        "чтобы их можно было слушать на ходу, а не читать с экрана.\n\n"
        "1. Выберите сценарий ниже — я подберу голос, темп и паузы\n"
        "2. Пришлите текст или файл .txt — верну mp3\n\n"
        f"{modes_list()}\n\n"
        f"{current_line(message.from_user.id)}\n"
        "Сменить голос — /voice, что умею и чего не делаю — /help",
        reply_markup=modes_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    await message.answer(
        f"{current_line(message.from_user.id)}\n\nВыберите сценарий:\n\n{modes_list()}",
        reply_markup=modes_keyboard(),
    )


@router.message(Command("voice"))
async def cmd_voice(message: Message) -> None:
    await message.answer(
        f"{current_line(message.from_user.id)}\n\nВыберите голос:\n\n{voices_list()}",
        reply_markup=voices_keyboard(),
    )


@router.message(Command("quota"))
async def cmd_quota(message: Message) -> None:
    usage = await voice.quota()
    if usage is None:
        await message.answer(
            "Не удалось узнать остаток: у ключа ElevenLabs нет права <i>User → Read</i>. "
            "Его можно включить в кабинете ElevenLabs → Developers → API Keys."
        )
        return
    used, limit = usage
    await message.answer(f"Использовано {used} из {limit} символов. Осталось: <b>{limit - used}</b>.")


@router.callback_query(F.data.startswith("mode:"))
async def on_mode_selected(callback: CallbackQuery) -> None:
    mode = callback.data.removeprefix("mode:")
    if mode not in config.MODES:
        await callback.answer("Этот режим больше недоступен", show_alert=True)
        return
    preset = config.MODES[mode]
    update_settings(callback.from_user.id, mode=mode, voice=preset["voice"])
    await callback.answer(preset["title"])
    await callback.message.answer(
        f"Режим {preset['title']}, голос <b>{config.VOICES[preset['voice']][0]}</b>.\n"
        "Пришлите текст инструкции или файл .txt. Другой голос — /voice"
    )


@router.callback_query(F.data.startswith("voice:"))
async def on_voice_selected(callback: CallbackQuery) -> None:
    voice_id = callback.data.removeprefix("voice:")
    if voice_id not in config.VOICES:
        await callback.answer("Этот голос больше недоступен", show_alert=True)
        return
    update_settings(callback.from_user.id, voice=voice_id)
    name = config.VOICES[voice_id][0]
    await callback.answer(f"Голос: {name}")
    await callback.message.answer(f"Выбран голос <b>{name}</b>. Теперь пришлите текст для озвучки.")


@router.callback_query(F.data.startswith("preview:"))
async def on_preview(callback: CallbackQuery) -> None:
    voice_id = callback.data.removeprefix("preview:")
    if voice_id not in config.VOICES:
        await callback.answer("Этот голос больше недоступен", show_alert=True)
        return
    await callback.answer()
    url = await voice.preview_url(voice_id)
    if not url:
        await callback.message.answer("Пример для этого голоса сейчас недоступен.")
        return
    name, desc = config.VOICES[voice_id]
    await callback.message.answer_audio(url, title=f"Пример: {name}", caption=f"<b>{name}</b> — {desc}")


async def speak(message: Message, bot: Bot, text: str) -> None:
    mode, voice_id = get_settings(message.from_user.id)
    preset = config.MODES[mode]
    prepared = text_prep.prepare(text, preset["step_word"], preset["pause"])
    length = text_prep.spoken_length(prepared)
    if not length:
        await message.answer("В тексте не осталось слов для озвучки — пришлите обычный текст.")
        return
    if length > config.MAX_TEXT_LENGTH:
        await message.answer(
            f"Текст слишком длинный: {length} символов, максимум {config.MAX_TEXT_LENGTH}. "
            "Разделите инструкцию на разделы и пришлите по очереди."
        )
        return

    parts = text_prep.split(prepared, config.CHUNK_SIZE)
    name = config.VOICES[voice_id][0]
    header = f"Озвучиваю: {length} символов · {preset['title']} · {name}"
    status = await message.answer(f"{header} ⏳")

    async def progress(done: int, total: int) -> None:
        await status.edit_text(f"{header}\nЧасть {done} из {total} ⏳")

    try:
        async with ChatActionSender.upload_voice(bot=bot, chat_id=message.chat.id):
            path = await voice.synthesize(parts, voice_id, mode, progress)
    except voice.VoiceError as e:
        await status.edit_text(f"⚠️ {e}")
        return

    title = text_prep.prepare(text.strip().splitlines()[0], preset["step_word"], 0)[:60]
    await message.answer_audio(
        FSInputFile(path),
        title=title,
        performer=f"{preset['title']} · {name}",
        caption=f"Файл сохранён: <code>audio/{path.name}</code>",
    )
    await status.delete()


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, bot: Bot) -> None:
    await speak(message, bot, message.text)


@router.message(F.document)
async def on_document(message: Message, bot: Bot) -> None:
    doc = message.document
    if not (doc.file_name or "").lower().endswith(".txt"):
        await message.answer("Я читаю только файлы .txt. Из Word: Файл → Сохранить как → Обычный текст (.txt).")
        return
    if doc.file_size and doc.file_size > config.MAX_FILE_SIZE:
        await message.answer("Файл больше 100 КБ — разделите инструкцию на части.")
        return
    raw = (await bot.download(doc)).read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1251", errors="replace")  # старые файлы из Блокнота Windows
    await speak(message, bot, text)


@router.message()
async def on_other(message: Message) -> None:
    await message.answer(
        "Я озвучиваю только текст: пришлите его сообщением или файлом .txt. "
        "Голосовые, фото и видео не обрабатываю. Справка — /help"
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_settings()
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать и выбрать сценарий"),
            BotCommand(command="mode", description="Сценарий: инструкция, обучение, памятка"),
            BotCommand(command="voice", description="Сменить голос"),
            BotCommand(command="help", description="Что подойдёт для озвучки и лимиты"),
            BotCommand(command="quota", description="Остаток символов ElevenLabs"),
        ]
    )
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
