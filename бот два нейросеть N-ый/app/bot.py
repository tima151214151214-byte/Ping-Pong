from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import time
from urllib.parse import urlparse

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.bible_gate import RULE_VIOLATION_TEXT, is_bible_question
from app.config import load_settings
from app.llm_client import LLMClient
from app.pipeline import run_pipeline
from app.storage import BotStorage


BOT_TITLE = "Православие простым языком"

ASK_BUTTON = "❓ Спросить вопрос"
QUOTA_BUTTON = "📊 Осталось запросов"
SETTINGS_BUTTON = "⚙️ Настройки"
API_HELP_BUTTON = "🔌 Как вставить свой API"
BACK_BUTTON = "⬅️ Назад"

ORTHODOX_BUTTON = "✝️ Православный"
CATHOLIC_BUTTON = "✝️ Католик"

LEN_VERY_SHORT_BUTTON = "📝 Очень коротко"
LEN_SHORT_BUTTON = "📝 Коротко"
LEN_MEDIUM_BUTTON = "📝 Средне"
LEN_LONG_BUTTON = "📝 Длинно"
LEN_VERY_LONG_BUTTON = "📝 Очень длинно"

STYLE_ORTHODOX_BUTTON = "🧠 По-православному"
STYLE_SIMPLE_BUTTON = "🙂 Простым языком"
STYLE_LAYERED_BUTTON = "🪜 Сложно → легко"

REASON_FAST_BUTTON = "⚡ Быстро"
REASON_BALANCED_BUTTON = "⚖️ Стандарт"
REASON_DEEP_BUTTON = "🐢 Глубоко"

MODEL_ROUTER_BUTTON = "🤖 Router Free"
MODEL_QWEN_BUTTON = "🤖 Qwen 4B"
MODEL_GPT_OSS_BUTTON = "🤖 GPT-OSS 20B"
MODEL_MISTRAL_BUTTON = "🤖 Mistral 24B"

DENOMINATION_BY_BUTTON = {
    ORTHODOX_BUTTON: "orthodox",
    CATHOLIC_BUTTON: "catholic",
}

ANSWER_LENGTH_BY_BUTTON = {
    LEN_VERY_SHORT_BUTTON: "very_short",
    LEN_SHORT_BUTTON: "short",
    LEN_MEDIUM_BUTTON: "medium",
    LEN_LONG_BUTTON: "long",
    LEN_VERY_LONG_BUTTON: "very_long",
}

EXPLAIN_STYLE_BY_BUTTON = {
    STYLE_ORTHODOX_BUTTON: "orthodox",
    STYLE_SIMPLE_BUTTON: "simple",
    STYLE_LAYERED_BUTTON: "layered",
}

REASONING_MODE_BY_BUTTON = {
    REASON_FAST_BUTTON: "fast",
    REASON_BALANCED_BUTTON: "balanced",
    REASON_DEEP_BUTTON: "deep",
}

MODEL_PRESET_BY_BUTTON = {
    MODEL_ROUTER_BUTTON: "router_free",
    MODEL_QWEN_BUTTON: "qwen_4b",
    MODEL_GPT_OSS_BUTTON: "gpt_oss_20b",
    MODEL_MISTRAL_BUTTON: "mistral_24b",
}

MODEL_BY_PRESET = {
    "router_free": "openrouter/free",
    "qwen_4b": "qwen/qwen3-4b:free",
    "gpt_oss_20b": "openai/gpt-oss-20b:free",
    "mistral_24b": "mistralai/mistral-small-3.1-24b-instruct:free",
}


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(ASK_BUTTON), KeyboardButton(QUOTA_BUTTON)],
            [KeyboardButton(SETTINGS_BUTTON), KeyboardButton(API_HELP_BUTTON)],
        ],
        resize_keyboard=True,
    )


def _settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(ORTHODOX_BUTTON), KeyboardButton(CATHOLIC_BUTTON)],
            [KeyboardButton(LEN_VERY_SHORT_BUTTON), KeyboardButton(LEN_SHORT_BUTTON)],
            [KeyboardButton(LEN_MEDIUM_BUTTON), KeyboardButton(LEN_LONG_BUTTON)],
            [KeyboardButton(LEN_VERY_LONG_BUTTON)],
            [KeyboardButton(STYLE_ORTHODOX_BUTTON), KeyboardButton(STYLE_SIMPLE_BUTTON)],
            [KeyboardButton(STYLE_LAYERED_BUTTON)],
            [KeyboardButton(REASON_FAST_BUTTON), KeyboardButton(REASON_BALANCED_BUTTON), KeyboardButton(REASON_DEEP_BUTTON)],
            [KeyboardButton(MODEL_ROUTER_BUTTON), KeyboardButton(MODEL_QWEN_BUTTON)],
            [KeyboardButton(MODEL_GPT_OSS_BUTTON), KeyboardButton(MODEL_MISTRAL_BUTTON)],
            [KeyboardButton(BACK_BUTTON)],
        ],
        resize_keyboard=True,
    )


def _split_message(text: str, chunk_size: int = 3900) -> list[str]:
    stripped = text.strip()
    if len(stripped) <= chunk_size:
        return [stripped]

    chunks: list[str] = []
    current = stripped
    while len(current) > chunk_size:
        split_at = current.rfind("\n", 0, chunk_size)
        if split_at < 500:
            split_at = chunk_size
        chunks.append(current[:split_at].strip())
        current = current[split_at:].strip()
    if current:
        chunks.append(current)
    return chunks


def _normalize_name(raw: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    if len(cleaned) < 2 or len(cleaned) > 40:
        return None
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-яЁё _\-]+", cleaned):
        return None
    return cleaned


def _format_context(history: list[tuple[str, str]], window: int) -> str:
    if not history:
        return ""

    rows: list[str] = []
    for idx, (question, answer) in enumerate(history[-window:], start=1):
        answer_short = answer.strip().replace("\n", " ")[:300]
        rows.append(f"{idx}) Вопрос: {question}\nОтвет: {answer_short}")
    return "\n\n".join(rows)


def _denomination_label(value: str) -> str:
    return "Католик" if value == "catholic" else "Православный"


def _answer_length_label(value: str) -> str:
    return {
        "very_short": "Очень коротко",
        "short": "Коротко",
        "medium": "Средне",
        "long": "Длинно",
        "very_long": "Очень длинно",
    }.get(value, "Длинно")


def _explain_style_label(value: str) -> str:
    return {
        "orthodox": "По-православному",
        "simple": "Простым языком",
        "layered": "Сложно → легко",
    }.get(value, "По-православному")


def _reasoning_mode_label(value: str) -> str:
    return {
        "fast": "Быстро",
        "balanced": "Стандарт",
        "deep": "Глубоко",
    }.get(value, "Стандарт")


def _model_preset_label(value: str) -> str:
    return {
        "router_free": "Router Free",
        "qwen_4b": "Qwen 4B",
        "gpt_oss_20b": "GPT-OSS 20B",
        "mistral_24b": "Mistral 24B",
    }.get(value, "Router Free")


def _selected_model(default_model: str, preset: str) -> tuple[str, list[str]]:
    if preset == "router_free":
        model = default_model.strip() or "openrouter/free"
        return model, [model, model, model, model]

    selected = MODEL_BY_PRESET.get(preset, default_model.strip() or "openrouter/free")
    return selected, [selected, selected, selected, selected]


def _progress_bar(percent: int, width: int = 20) -> str:
    safe = max(0, min(100, percent))
    filled = int(round((safe / 100) * width))
    return f"{'█' * filled}{'░' * (width - filled)}"


def _progress_text(percent: int, stage: str) -> str:
    safe = max(0, min(100, percent))
    return (
        "Обработка запроса...\n"
        f"[{_progress_bar(safe)}] {safe}%\n"
        f"Этап: {stage}"
    )


def _setup_instructions(default_base_url: str = "", default_model: str = "") -> str:
    base_hint = default_base_url.strip() or "https://openrouter.ai/api/v1"
    model_hint = default_model.strip() or "openrouter/free"
    return (
        "Подключение личного IP/API (можно быстро):\n\n"
        "Полный формат:\n"
        "`/connect <BASE_URL/IP> <API_KEY> [MODEL]`\n\n"
        "Быстрый формат (только ключ):\n"
        "`/connect <API_KEY>`\n"
        f"(BASE_URL и MODEL подставятся автоматически: `{base_hint}`, `{model_hint}`)\n\n"
        "Быстрый формат (только URL/IP):\n"
        "`/connect <BASE_URL/IP>`\n"
        "(ключ и модель будут взяты из настроек сервера)\n\n"
        "Пример OpenRouter:\n"
        "`/connect https://openrouter.ai/api/v1 sk-or-xxx openrouter/free`\n\n"
        "Пример локального IP (Ollama):\n"
        "`/connect http://192.168.1.20:11434/v1 ollama qwen2.5:7b`"
    )


def _looks_like_url(value: str) -> bool:
    return re.match(r"^https?://", value.strip(), flags=re.IGNORECASE) is not None


def _is_local_url(url: str) -> bool:
    try:
        host = (urlparse(url.strip()).hostname or "").lower()
    except Exception:
        return False

    if not host:
        return False
    if host == "localhost":
        return True

    try:
        parsed_ip = ipaddress.ip_address(host)
    except ValueError:
        return False

    return parsed_ip.is_private or parsed_ip.is_loopback


def _parse_connect_payload(
    text: str,
    default_base_url: str = "",
    default_api_key: str = "",
    default_model: str = "openrouter/free",
) -> tuple[str, str, str] | None:
    raw = text.strip()
    if not raw:
        return None

    if raw.startswith("/connect"):
        raw = raw[len("/connect") :].strip()

    if not raw:
        return None

    fallback_url = default_base_url.strip()
    fallback_key = default_api_key.strip()
    fallback_model = default_model.strip() or "openrouter/free"

    lowered = raw.lower()
    if "ip:" in lowered or "url:" in lowered or "key:" in lowered or "model:" in lowered:
        base_url = fallback_url
        api_key = fallback_key
        model = fallback_model
        for line in raw.splitlines():
            part = line.strip()
            if not part or ":" not in part:
                continue
            key, value = part.split(":", maxsplit=1)
            k = key.strip().lower()
            v = value.strip()
            if k in {"ip", "url", "base_url", "baseurl"}:
                base_url = v
            elif k in {"key", "api_key", "apikey", "token"}:
                api_key = v
            elif k == "model":
                model = v or model
        return _validate_connect(base_url, api_key, model)

    parts = raw.split()
    if not parts:
        return None

    if len(parts) == 1:
        token = parts[0].strip()
        if _looks_like_url(token):
            base_url = token
            api_key = fallback_key
            model = fallback_model
        else:
            base_url = fallback_url
            api_key = token
            model = fallback_model
        return _validate_connect(base_url, api_key, model)

    if len(parts) == 2:
        first = parts[0].strip()
        second = parts[1].strip()
        if _looks_like_url(first):
            base_url = first
            api_key = second
            model = fallback_model
        elif _looks_like_url(second):
            base_url = second
            api_key = first
            model = fallback_model
        else:
            base_url = fallback_url
            api_key = first
            model = second or fallback_model
        return _validate_connect(base_url, api_key, model)

    base_url = parts[0].strip()
    api_key = parts[1].strip()
    model = parts[2].strip() if len(parts) >= 3 else fallback_model
    return _validate_connect(base_url, api_key, model)


def _validate_connect(base_url: str, api_key: str, model: str) -> tuple[str, str, str] | None:
    url = base_url.strip().rstrip("/")
    key = api_key.strip()
    mdl = model.strip() or "openrouter/free"

    if not url or not _looks_like_url(url):
        return None
    if key and len(key) < 3:
        return None
    if not key and not _is_local_url(url):
        return None
    return (url, key, mdl)


def build_application() -> Application:
    settings = load_settings()
    storage = BotStorage(settings.storage_path)
    default_base_url = settings.llm_base_url.strip().rstrip("/")
    default_api_key = settings.llm_api_key.strip()
    default_model = settings.llm_model.strip() or "openrouter/free"
    setup_instructions = _setup_instructions(default_base_url=default_base_url, default_model=default_model)

    def default_ai_config() -> dict[str, str] | None:
        parsed = _validate_connect(default_base_url, default_api_key, default_model)
        if not parsed:
            return None
        base_url, api_key, model = parsed
        return {"base_url": base_url, "api_key": api_key, "model": model}

    def resolve_ai_config(chat_id: int) -> tuple[dict[str, str] | None, str]:
        personal = storage.get_ai_config(chat_id)
        if personal is not None:
            return personal, "personal"
        fallback = default_ai_config()
        if fallback is not None:
            return fallback, "default"
        return None, "missing"

    def on_request_complete() -> None:
        storage.increment_api_calls(1)

    def make_llm(ai_cfg: dict[str, str]) -> LLMClient:
        return LLMClient(
            base_url=ai_cfg["base_url"],
            api_key=ai_cfg["api_key"],
            model=ai_cfg["model"],
            timeout_seconds=settings.llm_timeout_seconds,
            on_request_complete=on_request_complete,
        )

    def quota_text() -> str:
        used = storage.get_api_calls_today()
        remaining = max(settings.daily_api_limit - used, 0)
        approx_answers = remaining // 8
        return (
            "Лимит на сегодня (OpenRouter API):\n"
            f"- Использовано: {used}/{settings.daily_api_limit}\n"
            f"- Осталось: {remaining}\n"
            f"- Примерно полноценных ответов бота: {approx_answers}"
        )

    def settings_text(user: dict[str, str], ai_cfg: dict[str, str], ai_source: str) -> str:
        source_label = "Личный IP/API" if ai_source == "personal" else "Серверный IP/API по умолчанию"
        return (
            f"{BOT_TITLE}: текущие настройки\n"
            f"- Конфессия: {_denomination_label(user.get('denomination', 'orthodox'))}\n"
            f"- Длина ответа: {_answer_length_label(user.get('answer_length', 'long'))}\n"
            f"- Как объяснять: {_explain_style_label(user.get('explain_style', 'orthodox'))}\n"
            f"- Скорость размышления: {_reasoning_mode_label(user.get('reasoning_mode', 'balanced'))}\n"
            f"- Модель: {_model_preset_label(user.get('model_preset', 'router_free'))}\n"
            f"- Источник подключения: {source_label}\n"
            f"- Подключённый IP/API: {ai_cfg.get('base_url', 'не задан')}\n"
            f"- Базовая модель IP/API: {ai_cfg.get('model', 'не задан')}\n\n"
            "Используй кнопки ниже, чтобы изменить параметры."
        )

    async def open_settings(
        update: Update,
        user: dict[str, str],
        ai_cfg: dict[str, str],
        ai_source: str,
    ) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            settings_text(user, ai_cfg, ai_source),
            reply_markup=_settings_keyboard(),
        )

    async def connect_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return

        chat_id = update.effective_chat.id
        payload = "/connect " + " ".join(context.args) if context.args else update.message.text
        parsed = _parse_connect_payload(
            payload,
            default_base_url=default_base_url,
            default_api_key=default_api_key,
            default_model=default_model,
        )
        if not parsed:
            await update.message.reply_text(
                "Не понял формат подключения.\n\n" + setup_instructions,
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        base_url, api_key, model = parsed
        storage.upsert_ai_config(chat_id=chat_id, base_url=base_url, api_key=api_key, model=model)

        context.user_data["awaiting_ai_config"] = False

        user = storage.get_user(chat_id)
        if user is None:
            context.user_data["awaiting_name"] = True
            await update.message.reply_text(
                "Личный IP/API сохранён. Теперь регистрация: отправь имя.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await update.message.reply_text(
            "Личный IP/API обновлён. Можно пользоваться ботом.",
            reply_markup=_menu_keyboard(),
        )

    async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return

        chat_id = update.effective_chat.id
        ai_cfg, ai_source = resolve_ai_config(chat_id)
        if ai_cfg is None:
            context.user_data["awaiting_ai_config"] = True
            context.user_data["awaiting_name"] = False
            context.user_data["settings_mode"] = False
            await update.message.reply_text(
                f"Привет. Это бот «{BOT_TITLE}».\n\n" + setup_instructions,
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        user = storage.get_user(chat_id)
        context.user_data["awaiting_question"] = False
        context.user_data["awaiting_ai_config"] = False

        if user is None:
            context.user_data["awaiting_name"] = True
            context.user_data["settings_mode"] = False
            await update.message.reply_text(
                "Подключение готово. Теперь регистрация: отправь имя (2-40 символов).",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        context.user_data["awaiting_name"] = False
        context.user_data["settings_mode"] = False
        source_label = "личный" if ai_source == "personal" else "серверный по умолчанию"
        await update.message.reply_text(
            f"С возвращением, {user['name']}! Это {BOT_TITLE}. Подключение: {source_label}. Выбери действие:",
            reply_markup=_menu_keyboard(),
        )

    async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(
            f"{BOT_TITLE}\n\n"
            "Схема работы:\n"
            "1) Если на сервере уже есть API, бот подставит его автоматически.\n"
            "2) Можно задать личный API через /connect (полный или короткий формат).\n"
            "3) После регистрации задавай вопросы.\n\n"
            "Кнопки:\n"
            "- ❓ Спросить вопрос\n"
            "- 📊 Осталось запросов\n"
            "- ⚙️ Настройки\n"
            "- 🔌 Как вставить свой API",
            reply_markup=_menu_keyboard(),
        )

    async def setup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(setup_instructions, reply_markup=_menu_keyboard())

    async def quota_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        await update.message.reply_text(quota_text(), reply_markup=_menu_keyboard())

    async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        ai_cfg, ai_source = resolve_ai_config(chat_id)
        if ai_cfg is None:
            context.user_data["awaiting_ai_config"] = True
            await update.message.reply_text(
                "Сначала подключи IP/API.\n\n" + setup_instructions,
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        user = storage.get_user(chat_id)
        if user is None:
            context.user_data["awaiting_name"] = True
            await update.message.reply_text(
                "Сначала регистрация. Отправь имя.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        context.user_data["settings_mode"] = True
        await open_settings(update, user, ai_cfg, ai_source)

    async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        context.user_data["settings_mode"] = False
        await update.message.reply_text("Меню:", reply_markup=_menu_keyboard())

    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text or not update.effective_chat:
            return

        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        if not text:
            return

        ai_cfg, ai_source = resolve_ai_config(chat_id)

        if text == API_HELP_BUTTON:
            await update.message.reply_text(setup_instructions, reply_markup=_menu_keyboard())
            return

        lowered = text.lower()
        is_connect_shortcut = (
            (" " not in text and (_looks_like_url(text) or lowered.startswith("sk-")))
            or ("key:" in lowered or "ip:" in lowered or "url:" in lowered or "model:" in lowered)
        )
        should_try_connect = bool(context.user_data.get("awaiting_ai_config")) or ai_cfg is None or is_connect_shortcut

        if should_try_connect:
            parsed = _parse_connect_payload(
                text,
                default_base_url=default_base_url,
                default_api_key=default_api_key,
                default_model=default_model,
            )
            if not parsed:
                if context.user_data.get("awaiting_ai_config") or ai_cfg is None or is_connect_shortcut:
                    await update.message.reply_text(
                        "Нужен IP/API перед регистрацией.\n\n" + setup_instructions,
                        reply_markup=ReplyKeyboardRemove(),
                    )
                return

            base_url, api_key, model = parsed
            storage.upsert_ai_config(chat_id=chat_id, base_url=base_url, api_key=api_key, model=model)
            context.user_data["awaiting_ai_config"] = False
            ai_cfg, ai_source = resolve_ai_config(chat_id)
            if ai_cfg is None:
                await update.message.reply_text(
                    "Не получилось сохранить подключение. Проверь формат:\n\n" + setup_instructions,
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            if storage.get_user(chat_id) is None:
                context.user_data["awaiting_name"] = True
                await update.message.reply_text(
                    "Личный IP/API сохранён. Теперь отправь имя для регистрации.",
                    reply_markup=ReplyKeyboardRemove(),
                )
            else:
                await update.message.reply_text(
                    "Личный IP/API сохранён.",
                    reply_markup=_menu_keyboard(),
                )
            return

        user = storage.get_user(chat_id)

        if context.user_data.get("awaiting_name"):
            name = _normalize_name(text)
            if name is None:
                await update.message.reply_text(
                    "Имя не подходит. Используй 2-40 символов: буквы, цифры, пробел, дефис.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            storage.upsert_user(chat_id=chat_id, name=name)
            context.user_data["awaiting_name"] = False
            context.user_data["awaiting_question"] = False
            context.user_data["last_topic_bible"] = False
            context.user_data["settings_mode"] = False

            await update.message.reply_text(
                f"Регистрация завершена, {name}. Выбери действие:",
                reply_markup=_menu_keyboard(),
            )
            return

        if user is None:
            context.user_data["awaiting_name"] = True
            await update.message.reply_text(
                "Сначала регистрация. Отправь имя.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        if text == QUOTA_BUTTON:
            context.user_data["settings_mode"] = False
            await update.message.reply_text(quota_text(), reply_markup=_menu_keyboard())
            return

        if text == ASK_BUTTON:
            context.user_data["awaiting_question"] = True
            context.user_data["settings_mode"] = False
            await update.message.reply_text(
                "Напиши вопрос по теме Библии/Бога.\n"
                "Пример: Что в Библии сказано о прощении?",
                reply_markup=_menu_keyboard(),
            )
            return

        if text == SETTINGS_BUTTON:
            context.user_data["settings_mode"] = True
            await open_settings(update, user, ai_cfg, ai_source)
            return

        if text == BACK_BUTTON:
            context.user_data["settings_mode"] = False
            await update.message.reply_text("Возврат в меню.", reply_markup=_menu_keyboard())
            return

        if text in DENOMINATION_BY_BUTTON:
            storage.update_denomination(chat_id=chat_id, denomination=DENOMINATION_BY_BUTTON[text])
            user = storage.get_user(chat_id) or user
            context.user_data["settings_mode"] = True
            await update.message.reply_text("Конфессия обновлена.", reply_markup=_settings_keyboard())
            await update.message.reply_text(settings_text(user, ai_cfg, ai_source), reply_markup=_settings_keyboard())
            return

        if text in ANSWER_LENGTH_BY_BUTTON:
            storage.update_answer_length(chat_id=chat_id, answer_length=ANSWER_LENGTH_BY_BUTTON[text])
            user = storage.get_user(chat_id) or user
            context.user_data["settings_mode"] = True
            await update.message.reply_text("Длина ответа обновлена.", reply_markup=_settings_keyboard())
            await update.message.reply_text(settings_text(user, ai_cfg, ai_source), reply_markup=_settings_keyboard())
            return

        if text in EXPLAIN_STYLE_BY_BUTTON:
            storage.update_explain_style(chat_id=chat_id, explain_style=EXPLAIN_STYLE_BY_BUTTON[text])
            user = storage.get_user(chat_id) or user
            context.user_data["settings_mode"] = True
            await update.message.reply_text("Стиль объяснения обновлён.", reply_markup=_settings_keyboard())
            await update.message.reply_text(settings_text(user, ai_cfg, ai_source), reply_markup=_settings_keyboard())
            return

        if text in REASONING_MODE_BY_BUTTON:
            storage.update_reasoning_mode(chat_id=chat_id, reasoning_mode=REASONING_MODE_BY_BUTTON[text])
            user = storage.get_user(chat_id) or user
            context.user_data["settings_mode"] = True
            await update.message.reply_text("Режим размышления обновлён.", reply_markup=_settings_keyboard())
            await update.message.reply_text(settings_text(user, ai_cfg, ai_source), reply_markup=_settings_keyboard())
            return

        if text in MODEL_PRESET_BY_BUTTON:
            storage.update_model_preset(chat_id=chat_id, model_preset=MODEL_PRESET_BY_BUTTON[text])
            user = storage.get_user(chat_id) or user
            context.user_data["settings_mode"] = True
            await update.message.reply_text("Модель обновлена.", reply_markup=_settings_keyboard())
            await update.message.reply_text(settings_text(user, ai_cfg, ai_source), reply_markup=_settings_keyboard())
            return

        if context.user_data.get("settings_mode"):
            await update.message.reply_text(
                "Используй кнопки настроек или нажми ⬅️ Назад.",
                reply_markup=_settings_keyboard(),
            )
            return

        question = text
        context.user_data["awaiting_question"] = False

        used_calls = storage.get_api_calls_today()
        remaining_calls = max(settings.daily_api_limit - used_calls, 0)
        if remaining_calls <= 0:
            await update.message.reply_text(
                "Дневной лимит API-запросов исчерпан. Попробуй завтра.\n\n"
                f"{quota_text()}",
                reply_markup=_menu_keyboard(),
            )
            return

        history = storage.get_short_memory(chat_id=chat_id, window=settings.history_window)
        context_excerpt = _format_context(history=history, window=settings.history_window)

        model_preset = str(user.get("model_preset", "router_free"))
        gate_model, agent_models = _selected_model(ai_cfg.get("model", "openrouter/free"), model_preset)

        progress_message = await update.message.reply_text(_progress_text(0, "Подготовка"))
        progress_state = {
            "percent": -1,
            "stage": "",
            "last_edit": 0.0,
        }

        async def progress(percent: int, stage: str) -> None:
            safe = max(0, min(100, int(percent)))
            now = time.monotonic()
            last_percent = int(progress_state["percent"])
            last_stage = str(progress_state["stage"])
            last_edit = float(progress_state["last_edit"])

            if safe == last_percent and stage == last_stage:
                return
            if (
                safe < 100
                and last_percent >= 0
                and now - last_edit < 0.7
                and safe - last_percent < 4
            ):
                return

            try:
                await progress_message.edit_text(_progress_text(safe, stage))
            except Exception:
                return

            progress_state["percent"] = safe
            progress_state["stage"] = stage
            progress_state["last_edit"] = now

        llm = make_llm(ai_cfg)

        await progress(5, "Проверяю тему вопроса")
        allowed = await is_bible_question(
            question=question,
            llm=llm,
            context_excerpt=context_excerpt,
            last_topic_bible=bool(context.user_data.get("last_topic_bible")),
            model=gate_model,
        )
        if not allowed:
            context.user_data["last_topic_bible"] = False
            try:
                await progress_message.delete()
            except Exception:
                pass
            await update.message.reply_text(
                RULE_VIOLATION_TEXT,
                reply_markup=_menu_keyboard(),
            )
            return

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await progress(12, "Запускаю анализ")

        try:
            result = await run_pipeline(
                llm=llm,
                question=question,
                web_results=settings.web_results,
                temperature=settings.request_temperature,
                context_excerpt=context_excerpt,
                agent_models=agent_models,
                denomination=str(user.get("denomination", "orthodox")),
                answer_length=str(user.get("answer_length", "long")),
                explain_style=str(user.get("explain_style", "orthodox")),
                reasoning_mode=str(user.get("reasoning_mode", "balanced")),
                progress_callback=progress,
            )
        except Exception:
            logger.exception("Pipeline failed")
            try:
                await progress_message.edit_text("Ошибка при обработке запроса. Попробуйте через минуту.")
            except Exception:
                pass
            return

        context.user_data["last_topic_bible"] = True
        storage.append_short_memory(
            chat_id=chat_id,
            question=question,
            answer=result.answer_text,
            window=settings.history_window,
        )

        await progress(100, "Готово")
        await asyncio.sleep(0.35)
        try:
            await progress_message.delete()
        except Exception:
            pass

        for chunk in _split_message(result.answer_text):
            await update.message.reply_text(
                chunk,
                disable_web_page_preview=True,
                reply_markup=_menu_keyboard(),
            )

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.exception("Unhandled telegram error", exc_info=context.error)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("setup", setup_handler))
    app.add_handler(CommandHandler("connect", connect_handler))
    app.add_handler(CommandHandler("quota", quota_handler))
    app.add_handler(CommandHandler("settings", settings_handler))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)
    return app


def run() -> None:
    app = build_application()
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)
