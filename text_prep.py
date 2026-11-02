"""Подготовка текста инструкции к озвучке.

Смысл и формулировки не меняются — убирается только то, что синтезатор речи прочитает
плохо или вслух: разметка, ссылки, эмодзи, символы-стрелки, сокращения. Нумерованные
пункты превращаются в «Шаг 1.», после каждого пункта ставится пауза.
"""

import re

# Сокращения, которые синтезатор читает по буквам или с запинкой
ABBREVIATIONS = {
    r"\bи т\.\s?д\.": "и так далее",
    r"\bи т\.\s?п\.": "и тому подобное",
    r"\bт\.\s?е\.": "то есть",
    r"\bт\.\s?к\.": "так как",
    r"\bнапр\.": "например",
    r"\bсм\.": "смотрите",
    r"\bприм\.": "примечание",
    r"\bдр\.": "другие",
}

SYMBOLS = {
    "°C": " градусов",
    "°С": " градусов",  # кириллическая С
    "°": " градусов",
    "№": "номер ",
    "&": " и ",
    "→": " — ",
    "->": " — ",
    "=>": " — ",
    "…": "...",
}

NUMBERED = re.compile(r"^\s*(\d{1,3})[.)]\s+(.*)$")
BULLET = re.compile(r"^\s*[-–—•*·▪►✓✔]\s+(.*)$")
MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
URL = re.compile(r"(?:https?://|www\.)[^\s)\]]+")
# Эмодзи и пиктограммы: синтезатор либо молчит на них, либо произносит название
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0000FE0F\U0000200D\U00002B00-\U00002BFF]"
)
# Конец предложения, но не «Шаг 2.» — номер пункта не отрываем от его текста
SENTENCE_END = re.compile(r"(?<=\D[.!?])\s+")
AFTER_PAUSE = re.compile(r"(?<=/>)\s+")


def _clean_line(line: str) -> str:
    line = MD_LINK.sub(r"\1", line)
    line = URL.sub("ссылка в тексте", line)
    line = EMOJI.sub("", line)
    for src, dst in SYMBOLS.items():
        line = line.replace(src, dst)
    line = re.sub(r"^#{1,6}\s*", "", line)  # заголовки markdown
    line = re.sub(r"[*_`~<>]", "", line)  # выделение markdown; <> — чтобы не сломать теги пауз
    for pattern, dst in ABBREVIATIONS.items():
        line = re.sub(pattern, dst, line, flags=re.IGNORECASE)
    line = re.sub(r"([!?.])\1{2,}", r"\1", line)  # «!!!» → «!»
    return re.sub(r"\s+", " ", line).strip()


def _with_period(line: str) -> str:
    """Строка без знака в конце читается слитно со следующей — добавляем точку."""
    return line if line[-1] in ".!?:;" else line + "."


def prepare(text: str, step_word: str, pause: float) -> str:
    """Возвращает текст, готовый к озвучке: пункты списков разделены паузами."""
    brk = f' <break time="{pause:.1f}s" />' if pause else ""
    out: list[str] = []
    for raw in text.splitlines():
        if numbered := NUMBERED.match(raw):
            body = _clean_line(numbered.group(2))
            if body:
                out.append(f"{step_word} {numbered.group(1)}. {_with_period(body)}{brk}")
        elif bullet := BULLET.match(raw):
            body = _clean_line(bullet.group(1))
            if body:
                out.append(_with_period(body[0].upper() + body[1:]) + brk)
        elif line := _clean_line(raw):
            # короткая строка без точки — обычно заголовок; длинная — перенос абзаца
            out.append(_with_period(line) if len(line) < 80 else line)
    return " ".join(out)


def split(text: str, size: int) -> list[str]:
    """Режет текст на части не длиннее size: сначала по пунктам, потом по предложениям."""
    pieces = [s for unit in AFTER_PAUSE.split(text) for s in SENTENCE_END.split(unit)]
    parts: list[str] = []
    current = ""
    for sentence in pieces:
        if current and len(current) + len(sentence) + 1 > size:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def spoken_length(text: str) -> int:
    """Длина текста без тегов пауз — столько символов спишет ElevenLabs (примерно)."""
    return len(re.sub(r"<break[^>]*/>", "", text))
