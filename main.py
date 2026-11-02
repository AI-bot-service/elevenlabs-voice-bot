import asyncio
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
import voice

router = Router()

# Выбранный голос по user_id. Хранится в памяти — после перезапуска сбрасывается на голос по умолчанию.
user_voices: dict[int, str] = {}


def voices_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=f"🎙 {name}", callback_data=f"voice:{vid}"),
            InlineKeyboardButton(text="▶️ пример", callback_data=f"preview:{vid}"),
        ]
        for vid, (name, _) in config.VOICES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def voices_list() -> str:
    return "\n".join(f"<b>{name}</b> — {desc}" for name, desc in config.VOICES.values())


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я озвучиваю текст женским голосом с помощью ElevenLabs.\n\n"
        "1. Выберите голос ниже (▶️ — послушать пример)\n"
        "2. Пришлите текст — верну аудиофайл mp3\n\n"
        f"{voices_list()}\n\n"
        f"Максимум {config.MAX_TEXT_LENGTH} символов за раз. Сменить голос — /voice",
        reply_markup=voices_keyboard(),
    )


@router.message(Command("voice"))
async def cmd_voice(message: Message) -> None:
    current = config.VOICES[user_voices.get(message.from_user.id, config.DEFAULT_VOICE_ID)][0]
    await message.answer(
        f"Сейчас выбран голос <b>{current}</b>. Выберите другой:\n\n{voices_list()}",
        reply_markup=voices_keyboard(),
    )


@router.callback_query(F.data.startswith("voice:"))
async def on_voice_selected(callback: CallbackQuery) -> None:
    voice_id = callback.data.removeprefix("voice:")
    if voice_id not in config.VOICES:
        await callback.answer("Этот голос больше недоступен", show_alert=True)
        return
    user_voices[callback.from_user.id] = voice_id
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


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, bot: Bot) -> None:
    text = message.text.strip()
    if len(text) > config.MAX_TEXT_LENGTH:
        await message.answer(
            f"Текст слишком длинный: {len(text)} символов, максимум {config.MAX_TEXT_LENGTH}. "
            "Разбейте его на части и пришлите по очереди."
        )
        return

    voice_id = user_voices.get(message.from_user.id, config.DEFAULT_VOICE_ID)
    status = await message.answer("Озвучиваю… ⏳")
    try:
        async with ChatActionSender.upload_voice(bot=bot, chat_id=message.chat.id):
            path = await voice.synthesize(text, voice_id)
    except voice.VoiceError as e:
        await status.edit_text(f"⚠️ {e}")
        return

    await message.answer_audio(
        FSInputFile(path),
        title=text[:60],
        performer=f"ElevenLabs · {config.VOICES[voice_id][0]}",
        caption=f"Файл сохранён: <code>audio/{path.name}</code>",
    )
    await status.delete()


@router.message()
async def on_other(message: Message) -> None:
    await message.answer("Я понимаю только текст. Пришлите текст для озвучки или /start.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать и выбрать голос"),
            BotCommand(command="voice", description="Сменить голос"),
        ]
    )
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
