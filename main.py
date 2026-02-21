#!/usr/bin/env python3
import ast
import http.server
import json
import math
import os
import random
import re
import signal
import ssl
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "bot_state.sqlite3")
ENV_PATH = os.path.join(PROJECT_DIR, ".env")
POLL_TIMEOUT = 25
RETRY_DELAY = 3
MAX_EXPR_LEN = 220
MAX_RELAY_LEN = 700
PAGE_SIZE = 8
DEFAULT_ADMIN_PASSWORD = "151214"
GAME_ROUNDS = 5
GAME_QUESTION_TIMEOUT = 20
GAME_COUNTDOWN_DELAY = 1.0
REPORT_REASON_MAX_LEN = 400

BTN_CALC = "🧮 Начать считать"
BTN_HELP = "❓ Помощь"
BTN_SETTINGS = "⚙️ Настройки"
BTN_STATS = "📊 Статистика"
BTN_ONLINE = "🎮 Онлайн-игра"
BTN_FRIENDS = "👥 Друзья"
BTN_HOME = "🏠 Домой"

SENDER_BOT_KEY = "sender_bot_offset"
RECEIVER_BOT_KEY = "receiver_bot_offset"
ADMIN_KEY = "admin_user_id"
ADMIN_AUTOCLEAN_KEY = "admin_autoclean_seconds"

stop_event = threading.Event()
db_lock = threading.Lock()
admin_mode_lock = threading.Lock()
admin_auth_lock = threading.Lock()
receiver_reg_lock = threading.Lock()
receiver_mode_lock = threading.Lock()
receiver_queue_lock = threading.Lock()
receiver_game_lock = threading.Lock()
friend_invite_lock = threading.Lock()
receiver_report_lock = threading.Lock()
db = None
SENDER_BOT_TOKEN = ""
RECEIVER_BOT_TOKEN = ""
ADMIN_PASSWORD = DEFAULT_ADMIN_PASSWORD
SSL_CONTEXT = ssl.create_default_context()
admin_mode = {"type": None, "target_id": None, "target_ids": []}
admin_login_stage = {}
authenticated_admin_users = set()
receiver_registration_stage = {}
receiver_modes = {}
online_waiting_queue = []
online_waiting_set = set()
game_sessions = {}
chat_to_game = {}
game_seq = 0
friend_game_invites = {}
receiver_pending_reports = {}


class TelegramApiError(Exception):
    def __init__(self, error_code, description):
        self.error_code = error_code
        self.description = description
        super().__init__(f"{error_code}: {description}")


class CalcEvalError(Exception):
    pass


def load_env(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db():
    global db
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    db.row_factory = sqlite3.Row

    with db_lock:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_premium INTEGER NOT NULL DEFAULT 0,
                is_bot INTEGER NOT NULL DEFAULT 0,
                consent INTEGER NOT NULL DEFAULT 0,
                consent_at TEXT,
                broadcast_enabled INTEGER NOT NULL DEFAULT 1,
                registration_name TEXT,
                registered_at TEXT,
                class_group TEXT NOT NULL DEFAULT '5-8',
                allow_friend_requests INTEGER NOT NULL DEFAULT 1,
                searchable_by_name INTEGER NOT NULL DEFAULT 1,
                visit_count INTEGER NOT NULL DEFAULT 0,
                last_visit_at TEXT,
                is_banned INTEGER NOT NULL DEFAULT 0,
                ban_reason TEXT,
                ban_until TEXT,
                subscribed_at TEXT NOT NULL,
                last_seen_at TEXT,
                last_message_text TEXT,
                last_message_at TEXT,
                total_messages INTEGER NOT NULL DEFAULT 0,
                calc_success_count INTEGER NOT NULL DEFAULT 0,
                calc_failed_count INTEGER NOT NULL DEFAULT 0,
                relayed_count INTEGER NOT NULL DEFAULT 0,
                game_wins INTEGER NOT NULL DEFAULT 0,
                game_losses INTEGER NOT NULL DEFAULT 0,
                game_draws INTEGER NOT NULL DEFAULT 0,
                game_points INTEGER NOT NULL DEFAULT 0,
                last_calc_input TEXT,
                last_calc_output TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS friend_requests (
                requester_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(requester_id, target_id)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS friendships (
                user_low INTEGER NOT NULL,
                user_high INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                created_by INTEGER,
                PRIMARY KEY(user_low, user_high)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS player_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS registration_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                registration_name TEXT,
                registered_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_message_log (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(chat_id, message_id)
            )
            """
        )
        db.commit()

    migrate_subscribers_table()


def migrate_subscribers_table():
    columns_required = {
        "language_code": "ALTER TABLE subscribers ADD COLUMN language_code TEXT",
        "is_premium": "ALTER TABLE subscribers ADD COLUMN is_premium INTEGER NOT NULL DEFAULT 0",
        "is_bot": "ALTER TABLE subscribers ADD COLUMN is_bot INTEGER NOT NULL DEFAULT 0",
        "consent": "ALTER TABLE subscribers ADD COLUMN consent INTEGER NOT NULL DEFAULT 0",
        "consent_at": "ALTER TABLE subscribers ADD COLUMN consent_at TEXT",
        "broadcast_enabled": "ALTER TABLE subscribers ADD COLUMN broadcast_enabled INTEGER NOT NULL DEFAULT 1",
        "registration_name": "ALTER TABLE subscribers ADD COLUMN registration_name TEXT",
        "registered_at": "ALTER TABLE subscribers ADD COLUMN registered_at TEXT",
        "class_group": "ALTER TABLE subscribers ADD COLUMN class_group TEXT NOT NULL DEFAULT '5-8'",
        "allow_friend_requests": "ALTER TABLE subscribers ADD COLUMN allow_friend_requests INTEGER NOT NULL DEFAULT 1",
        "searchable_by_name": "ALTER TABLE subscribers ADD COLUMN searchable_by_name INTEGER NOT NULL DEFAULT 1",
        "visit_count": "ALTER TABLE subscribers ADD COLUMN visit_count INTEGER NOT NULL DEFAULT 0",
        "last_visit_at": "ALTER TABLE subscribers ADD COLUMN last_visit_at TEXT",
        "is_banned": "ALTER TABLE subscribers ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0",
        "ban_reason": "ALTER TABLE subscribers ADD COLUMN ban_reason TEXT",
        "ban_until": "ALTER TABLE subscribers ADD COLUMN ban_until TEXT",
        "last_seen_at": "ALTER TABLE subscribers ADD COLUMN last_seen_at TEXT",
        "last_message_text": "ALTER TABLE subscribers ADD COLUMN last_message_text TEXT",
        "last_message_at": "ALTER TABLE subscribers ADD COLUMN last_message_at TEXT",
        "total_messages": "ALTER TABLE subscribers ADD COLUMN total_messages INTEGER NOT NULL DEFAULT 0",
        "calc_success_count": "ALTER TABLE subscribers ADD COLUMN calc_success_count INTEGER NOT NULL DEFAULT 0",
        "calc_failed_count": "ALTER TABLE subscribers ADD COLUMN calc_failed_count INTEGER NOT NULL DEFAULT 0",
        "relayed_count": "ALTER TABLE subscribers ADD COLUMN relayed_count INTEGER NOT NULL DEFAULT 0",
        "game_wins": "ALTER TABLE subscribers ADD COLUMN game_wins INTEGER NOT NULL DEFAULT 0",
        "game_losses": "ALTER TABLE subscribers ADD COLUMN game_losses INTEGER NOT NULL DEFAULT 0",
        "game_draws": "ALTER TABLE subscribers ADD COLUMN game_draws INTEGER NOT NULL DEFAULT 0",
        "game_points": "ALTER TABLE subscribers ADD COLUMN game_points INTEGER NOT NULL DEFAULT 0",
        "last_calc_input": "ALTER TABLE subscribers ADD COLUMN last_calc_input TEXT",
        "last_calc_output": "ALTER TABLE subscribers ADD COLUMN last_calc_output TEXT",
    }
    with db_lock:
        existing = {row["name"] for row in db.execute("PRAGMA table_info(subscribers)").fetchall()}
        for column_name, statement in columns_required.items():
            if column_name not in existing:
                db.execute(statement)
        db.commit()


def get_setting(key):
    with db_lock:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key, value):
    with db_lock:
        db.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        db.commit()


def get_offset(key):
    value = get_setting(key)
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def set_offset(key, offset):
    set_setting(key, str(offset))


def get_admin_id():
    value = get_setting(ADMIN_KEY)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def set_admin_id(user_id):
    set_setting(ADMIN_KEY, str(user_id))


def get_admin_autoclean_seconds():
    value = get_setting(ADMIN_AUTOCLEAN_KEY)
    if value is None:
        return 0
    try:
        seconds = int(value)
    except ValueError:
        return 0
    return max(0, seconds)


def set_admin_autoclean_seconds(seconds):
    safe_seconds = max(0, int(seconds))
    set_setting(ADMIN_AUTOCLEAN_KEY, str(safe_seconds))


def format_duration(seconds):
    total = int(seconds)
    if total <= 0:
        return "выключено"
    if total % 86400 == 0:
        days = total // 86400
        return f"{days}д"
    if total % 3600 == 0:
        hours = total // 3600
        return f"{hours}ч"
    if total % 60 == 0:
        minutes = total // 60
        return f"{minutes}м"
    return f"{total}с"


def parse_autoclean_input(raw_value):
    text = (raw_value or "").strip().lower()
    if not text or text in {"off", "disable", "disabled", "выкл", "выключить", "0"}:
        return 0, None

    match = re.fullmatch(r"(\d+)\s*([a-zа-я]+)", text, flags=re.IGNORECASE)
    if not match:
        return None, "Формат: off | 10m | 1h | 12h | 1d"

    amount = int(match.group(1))
    unit = match.group(2).lower()
    unit_map = {
        "m": 60,
        "min": 60,
        "mins": 60,
        "minute": 60,
        "minutes": 60,
        "м": 60,
        "мин": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
        "hour": 3600,
        "hours": 3600,
        "ч": 3600,
        "час": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "д": 86400,
        "дн": 86400,
    }
    if unit not in unit_map:
        return None, "Формат: off | 10m | 1h | 12h | 1d"
    seconds = amount * unit_map[unit]
    if seconds < 60 or seconds > 7 * 86400:
        return None, "Интервал автоочистки: от 1 минуты до 7 дней."
    return seconds, None


def log_admin_message(chat_id, message_id):
    with db_lock:
        db.execute(
            """
            INSERT OR REPLACE INTO admin_message_log(chat_id, message_id, created_at)
            VALUES(?, ?, ?)
            """,
            (int(chat_id), int(message_id), utc_now()),
        )
        db.commit()


def cleanup_admin_message_log(chat_id, message_ids):
    if not message_ids:
        return
    placeholders = ",".join("?" for _ in message_ids)
    with db_lock:
        db.execute(
            f"DELETE FROM admin_message_log WHERE chat_id = ? AND message_id IN ({placeholders})",
            (int(chat_id), *[int(mid) for mid in message_ids]),
        )
        db.commit()


def maybe_cleanup_admin_chat(chat_id, limit=40):
    ttl_seconds = get_admin_autoclean_seconds()
    if ttl_seconds <= 0:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with db_lock:
        rows = db.execute(
            """
            SELECT message_id
            FROM admin_message_log
            WHERE chat_id = ? AND created_at <= ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (int(chat_id), cutoff, int(limit)),
        ).fetchall()
    if not rows:
        return 0
    removed_ids = []
    for row in rows:
        message_id = int(row["message_id"])
        try:
            delete_message(SENDER_BOT_TOKEN, int(chat_id), message_id)
        except Exception:  # noqa: BLE001
            pass
        removed_ids.append(message_id)
    cleanup_admin_message_log(chat_id, removed_ids)
    return len(removed_ids)


def set_admin_mode(mode_type=None, target_id=None, target_ids=None):
    if target_ids is None:
        target_ids = []
    with admin_mode_lock:
        admin_mode["type"] = mode_type
        admin_mode["target_id"] = target_id
        admin_mode["target_ids"] = list(target_ids)


def get_admin_mode():
    with admin_mode_lock:
        return dict(admin_mode)


def begin_admin_auth(user_id):
    with admin_auth_lock:
        admin_login_stage[int(user_id)] = 1
        authenticated_admin_users.discard(int(user_id))


def get_admin_auth_stage(user_id):
    with admin_auth_lock:
        return admin_login_stage.get(int(user_id))


def set_admin_auth_stage(user_id, stage):
    with admin_auth_lock:
        admin_login_stage[int(user_id)] = int(stage)


def clear_admin_auth(user_id):
    with admin_auth_lock:
        admin_login_stage.pop(int(user_id), None)
        authenticated_admin_users.discard(int(user_id))


def set_admin_authenticated(user_id, authenticated):
    with admin_auth_lock:
        admin_login_stage.pop(int(user_id), None)
        if authenticated:
            authenticated_admin_users.add(int(user_id))
        else:
            authenticated_admin_users.discard(int(user_id))


def is_admin_authenticated(user_id):
    with admin_auth_lock:
        return int(user_id) in authenticated_admin_users


def begin_receiver_registration(chat_id):
    with receiver_reg_lock:
        receiver_registration_stage[int(chat_id)] = True


def clear_receiver_registration(chat_id):
    with receiver_reg_lock:
        receiver_registration_stage.pop(int(chat_id), None)


def is_receiver_registration_pending(chat_id):
    with receiver_reg_lock:
        return bool(receiver_registration_stage.get(int(chat_id)))


def set_receiver_mode(chat_id, mode_name):
    with receiver_mode_lock:
        receiver_modes[int(chat_id)] = mode_name


def get_receiver_mode(chat_id):
    with receiver_mode_lock:
        return receiver_modes.get(int(chat_id), "home")


def clear_receiver_mode(chat_id):
    with receiver_mode_lock:
        receiver_modes.pop(int(chat_id), None)


def set_pending_report_target(chat_id, target_id):
    with receiver_report_lock:
        receiver_pending_reports[int(chat_id)] = int(target_id)


def get_pending_report_target(chat_id):
    with receiver_report_lock:
        target = receiver_pending_reports.get(int(chat_id))
    return int(target) if target is not None else None


def clear_pending_report_target(chat_id):
    with receiver_report_lock:
        receiver_pending_reports.pop(int(chat_id), None)


def clear_pending_reports_related(chat_id):
    user_id = int(chat_id)
    with receiver_report_lock:
        receiver_pending_reports.pop(user_id, None)
        stale = [src for src, target in receiver_pending_reports.items() if int(target) == user_id]
        for src in stale:
            receiver_pending_reports.pop(src, None)


def parse_chat_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_utc_timestamp(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.strptime(str(raw_value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def format_local_timestamp(raw_value):
    dt_utc = parse_utc_timestamp(raw_value)
    if dt_utc is None:
        return raw_value or "-"
    return dt_utc.astimezone().strftime("%Y-%m-%d %H:%M %Z")


def parse_ban_until_input(raw_value):
    text = (raw_value or "").strip().lower()
    if not text:
        return None, None, "Укажи время бана, например: 1h, 12h, 1d, 12:00."

    for prefix in ("до ", "на "):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()

    now_local = datetime.now().astimezone()

    duration_match = re.fullmatch(r"(\d+)\s*([a-zа-я]+)", text, flags=re.IGNORECASE)
    if duration_match:
        amount = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        units = {
            "m": 60,
            "min": 60,
            "mins": 60,
            "minute": 60,
            "minutes": 60,
            "мин": 60,
            "м": 60,
            "h": 3600,
            "hr": 3600,
            "hrs": 3600,
            "hour": 3600,
            "hours": 3600,
            "ч": 3600,
            "час": 3600,
            "d": 86400,
            "day": 86400,
            "days": 86400,
            "д": 86400,
            "дн": 86400,
        }
        if unit in units:
            target_local = now_local + timedelta(seconds=amount * units[unit])
            if target_local <= now_local:
                return None, None, "Время должно быть в будущем."
            return (
                target_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                target_local.strftime("%Y-%m-%d %H:%M %Z"),
                None,
            )

    hhmm_match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    if hhmm_match:
        hour = int(hhmm_match.group(1))
        minute = int(hhmm_match.group(2))
        if hour > 23 or minute > 59:
            return None, None, "Время в формате HH:MM."
        target_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_local <= now_local:
            target_local += timedelta(days=1)
        return (
            target_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            target_local.strftime("%Y-%m-%d %H:%M %Z"),
            None,
        )

    absolute_formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%d.%m.%Y %H:%M",
    ]
    for pattern in absolute_formats:
        try:
            parsed = datetime.strptime(text, pattern)
        except ValueError:
            continue
        target_local = parsed.replace(tzinfo=now_local.tzinfo)
        if target_local <= now_local:
            return None, None, "Время должно быть в будущем."
        return (
            target_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            target_local.strftime("%Y-%m-%d %H:%M %Z"),
            None,
        )

    dm_match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})", text)
    if dm_match:
        day = int(dm_match.group(1))
        month = int(dm_match.group(2))
        hour = int(dm_match.group(3))
        minute = int(dm_match.group(4))
        if hour > 23 or minute > 59:
            return None, None, "Время в формате DD.MM HH:MM."
        for year in [now_local.year, now_local.year + 1]:
            try:
                candidate = datetime(year, month, day, hour, minute, tzinfo=now_local.tzinfo)
            except ValueError:
                continue
            if candidate > now_local:
                return (
                    candidate.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    candidate.strftime("%Y-%m-%d %H:%M %Z"),
                    None,
                )
        return None, None, "Время должно быть в будущем."

    return None, None, "Не понял формат времени. Примеры: 1h, 12h, 1d, 12:00, 2026-02-20 18:30."


def ensure_user_row(chat_id):
    with db_lock:
        db.execute(
            """
            INSERT INTO subscribers(chat_id, subscribed_at)
            VALUES(?, ?)
            ON CONFLICT(chat_id) DO NOTHING
            """,
            (int(chat_id), utc_now()),
        )
        db.commit()


def normalize_registration_name(value):
    return " ".join((value or "").strip().split())


def is_registration_name_taken(registration_name, exclude_chat_id=None):
    normalized = normalize_registration_name(registration_name).lower()
    if not normalized:
        return False
    with db_lock:
        if exclude_chat_id is None:
            row = db.execute(
                """
                SELECT chat_id
                FROM subscribers
                WHERE registration_name IS NOT NULL
                  AND lower(trim(registration_name)) = ?
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
        else:
            row = db.execute(
                """
                SELECT chat_id
                FROM subscribers
                WHERE registration_name IS NOT NULL
                  AND lower(trim(registration_name)) = ?
                  AND chat_id != ?
                LIMIT 1
                """,
                (normalized, int(exclude_chat_id)),
            ).fetchone()
    return row is not None


def validate_registration_name(value):
    normalized = normalize_registration_name(value)
    if len(normalized) < 2 or len(normalized) > 60:
        return None, "Имя должно быть от 2 до 60 символов."
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9 _.-]+", normalized):
        return None, "Имя содержит запрещенные символы."
    return normalized, None


def touch_user(chat_id, user_obj, message_text=None):
    ensure_user_row(chat_id)
    now = utc_now()
    preview = (message_text or "").strip()
    if len(preview) > MAX_RELAY_LEN:
        preview = preview[:MAX_RELAY_LEN]
    if not preview:
        preview = None

    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET username = ?,
                first_name = ?,
                last_name = ?,
                language_code = ?,
                is_premium = ?,
                is_bot = ?,
                last_seen_at = ?,
                last_message_text = COALESCE(?, last_message_text),
                last_message_at = CASE WHEN ? IS NOT NULL THEN ? ELSE last_message_at END
            WHERE chat_id = ?
            """,
            (
                user_obj.get("username"),
                user_obj.get("first_name"),
                user_obj.get("last_name"),
                user_obj.get("language_code"),
                1 if user_obj.get("is_premium") else 0,
                1 if user_obj.get("is_bot") else 0,
                now,
                preview,
                preview,
                now,
                int(chat_id),
            ),
        )
        db.commit()


def increment_user_counters(
    chat_id,
    total=0,
    calc_success=0,
    calc_failed=0,
    relayed=0,
    last_calc_input=None,
    last_calc_output=None,
):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET total_messages = total_messages + ?,
                calc_success_count = calc_success_count + ?,
                calc_failed_count = calc_failed_count + ?,
                relayed_count = relayed_count + ?,
                last_calc_input = COALESCE(?, last_calc_input),
                last_calc_output = COALESCE(?, last_calc_output),
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (
                int(total),
                int(calc_success),
                int(calc_failed),
                int(relayed),
                last_calc_input,
                last_calc_output,
                utc_now(),
                int(chat_id),
            ),
        )
        db.commit()


def set_user_consent(chat_id, consent):
    ensure_user_row(chat_id)
    now = utc_now()
    with db_lock:
        if consent:
            db.execute(
                """
                UPDATE subscribers
                SET consent = 1,
                    consent_at = ?,
                    broadcast_enabled = 1,
                    registered_at = COALESCE(registered_at, ?),
                    last_seen_at = ?
                WHERE chat_id = ?
                """,
                (now, now, now, int(chat_id)),
            )
        else:
            db.execute(
                """
                UPDATE subscribers
                SET consent = 0,
                    consent_at = NULL,
                    broadcast_enabled = 0,
                    registered_at = NULL,
                    last_seen_at = ?
                WHERE chat_id = ?
                """,
                (now, int(chat_id)),
            )
        db.commit()


def set_user_registration_name(chat_id, registration_name):
    ensure_user_row(chat_id)
    normalized = normalize_registration_name(registration_name)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET registration_name = ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (normalized[:120] if normalized else None, utc_now(), int(chat_id)),
        )
        db.commit()


def set_user_class_group(chat_id, class_group):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET class_group = ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (class_group, utc_now(), int(chat_id)),
        )
        db.commit()


def set_user_allow_friend_requests(chat_id, enabled):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET allow_friend_requests = ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (1 if enabled else 0, utc_now(), int(chat_id)),
        )
        db.commit()


def set_user_searchable_by_name(chat_id, enabled):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET searchable_by_name = ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (1 if enabled else 0, utc_now(), int(chat_id)),
        )
        db.commit()


def friendship_pair(user_a, user_b):
    first = int(user_a)
    second = int(user_b)
    if first == second:
        return None
    return (first, second) if first < second else (second, first)


def are_friends(user_a, user_b):
    pair = friendship_pair(user_a, user_b)
    if pair is None:
        return False
    with db_lock:
        row = db.execute(
            """
            SELECT 1
            FROM friendships
            WHERE user_low = ? AND user_high = ?
            LIMIT 1
            """,
            pair,
        ).fetchone()
    return row is not None


def create_friendship(user_a, user_b, created_by=None):
    pair = friendship_pair(user_a, user_b)
    if pair is None:
        return False
    created_at = utc_now()
    with db_lock:
        db.execute(
            """
            INSERT INTO friendships(user_low, user_high, created_at, created_by)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(user_low, user_high) DO NOTHING
            """,
            (pair[0], pair[1], created_at, int(created_by) if created_by is not None else None),
        )
        db.commit()
    return True


def remove_friendship(user_a, user_b):
    pair = friendship_pair(user_a, user_b)
    if pair is None:
        return False
    with db_lock:
        cursor = db.execute(
            """
            DELETE FROM friendships
            WHERE user_low = ? AND user_high = ?
            """,
            pair,
        )
        db.commit()
    return cursor.rowcount > 0


def count_friends(chat_id):
    user_id = int(chat_id)
    with db_lock:
        row = db.execute(
            """
            SELECT COUNT(*) AS c
            FROM friendships
            WHERE user_low = ? OR user_high = ?
            """,
            (user_id, user_id),
        ).fetchone()
    return int(row["c"] if row else 0)


def list_friends(chat_id, limit=50, offset=0):
    user_id = int(chat_id)
    with db_lock:
        rows = db.execute(
            """
            SELECT s.chat_id, s.username, s.first_name, s.last_name, s.registration_name,
                   s.class_group, s.last_seen_at, s.visit_count, s.is_banned
            FROM friendships f
            JOIN subscribers s
              ON s.chat_id = CASE WHEN f.user_low = ? THEN f.user_high ELSE f.user_low END
            WHERE f.user_low = ? OR f.user_high = ?
            ORDER BY COALESCE(s.registration_name, s.username, s.first_name, s.last_name, CAST(s.chat_id AS TEXT)) COLLATE NOCASE ASC
            LIMIT ? OFFSET ?
            """,
            (user_id, user_id, user_id, int(limit), int(offset)),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_user_social_graph(chat_id):
    user_id = int(chat_id)
    with db_lock:
        db.execute(
            "DELETE FROM friend_requests WHERE requester_id = ? OR target_id = ?",
            (user_id, user_id),
        )
        db.execute(
            "DELETE FROM friendships WHERE user_low = ? OR user_high = ?",
            (user_id, user_id),
        )
        db.commit()


def list_incoming_friend_requests(chat_id, limit=30):
    user_id = int(chat_id)
    with db_lock:
        rows = db.execute(
            """
            SELECT s.chat_id, s.username, s.first_name, s.last_name, s.registration_name,
                   fr.created_at, fr.updated_at
            FROM friend_requests fr
            JOIN subscribers s ON s.chat_id = fr.requester_id
            WHERE fr.target_id = ? AND fr.status = 'pending'
            ORDER BY fr.updated_at DESC
            LIMIT ?
            """,
            (user_id, int(limit)),
        ).fetchall()
    return [dict(row) for row in rows]


def get_pending_friend_request(requester_id, target_id):
    with db_lock:
        row = db.execute(
            """
            SELECT requester_id, target_id, status, created_at, updated_at
            FROM friend_requests
            WHERE requester_id = ? AND target_id = ? AND status = 'pending'
            LIMIT 1
            """,
            (int(requester_id), int(target_id)),
        ).fetchone()
    return row_to_dict(row)


def respond_friend_request(target_id, requester_id, accept):
    target = int(target_id)
    requester = int(requester_id)
    pending = get_pending_friend_request(requester, target)
    if not pending:
        return False

    now = utc_now()
    new_status = "accepted" if accept else "rejected"
    with db_lock:
        db.execute(
            """
            UPDATE friend_requests
            SET status = ?,
                updated_at = ?
            WHERE requester_id = ? AND target_id = ? AND status = 'pending'
            """,
            (new_status, now, requester, target),
        )
        db.commit()

    if accept:
        create_friendship(requester, target, created_by=target)
    return True


def create_or_refresh_friend_request(requester_id, target_id):
    requester = int(requester_id)
    target = int(target_id)

    if requester == target:
        return "self"
    if are_friends(requester, target):
        return "already_friends"

    requester_row = get_user(requester)
    target_row = get_user(target)
    if not requester_row or not target_row:
        return "not_found"
    if not is_user_registered(requester) or not is_user_registered(target):
        return "not_registered"
    if int(target_row.get("allow_friend_requests") or 0) != 1:
        return "disabled"
    if is_user_banned(requester) or is_user_banned(target):
        return "banned"

    reverse_pending = get_pending_friend_request(target, requester)
    if reverse_pending:
        respond_friend_request(requester, target, accept=True)
        return "auto_accepted"

    existing = get_pending_friend_request(requester, target)
    if existing:
        return "already_pending"

    now = utc_now()
    with db_lock:
        db.execute(
            """
            INSERT INTO friend_requests(requester_id, target_id, status, created_at, updated_at)
            VALUES(?, ?, 'pending', ?, ?)
            ON CONFLICT(requester_id, target_id) DO UPDATE SET
                status = 'pending',
                updated_at = excluded.updated_at
            """,
            (requester, target, now, now),
        )
        db.commit()
    return "created"


def record_user_visit(chat_id):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET visit_count = visit_count + 1,
                last_visit_at = ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (utc_now(), utc_now(), int(chat_id)),
        )
        db.commit()


def update_user_game_stats(chat_id, wins=0, losses=0, draws=0, points=0):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET game_wins = game_wins + ?,
                game_losses = game_losses + ?,
                game_draws = game_draws + ?,
                game_points = game_points + ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (int(wins), int(losses), int(draws), int(points), utc_now(), int(chat_id)),
        )
        db.commit()


def set_user_banned(chat_id, banned, reason=None, until_at=None):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET is_banned = ?,
                ban_reason = ?,
                ban_until = ?,
                broadcast_enabled = CASE WHEN ? = 1 THEN 0 ELSE broadcast_enabled END,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (
                1 if banned else 0,
                (reason or "").strip()[:200] if banned else None,
                until_at if banned else None,
                1 if banned else 0,
                utc_now(),
                int(chat_id),
            ),
        )
        db.commit()
    if banned:
        clear_game_invites_for(chat_id)
        clear_pending_reports_related(chat_id)


def clear_expired_bans():
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET is_banned = 0,
                ban_reason = NULL,
                ban_until = NULL
            WHERE is_banned = 1
              AND ban_until IS NOT NULL
              AND ban_until <= ?
            """,
            (utc_now(),),
        )
        db.commit()


def is_user_banned(chat_id):
    with db_lock:
        row = db.execute(
            "SELECT is_banned, ban_until FROM subscribers WHERE chat_id = ?",
            (int(chat_id),),
        ).fetchone()
    if not row:
        return False
    if int(row["is_banned"] or 0) != 1:
        return False
    ban_until = parse_utc_timestamp(row["ban_until"])
    if ban_until is not None and ban_until <= datetime.now(timezone.utc):
        set_user_banned(chat_id, False)
        return False
    return True


def set_broadcast_enabled(chat_id, enabled):
    ensure_user_row(chat_id)
    with db_lock:
        db.execute(
            """
            UPDATE subscribers
            SET broadcast_enabled = ?,
                last_seen_at = ?
            WHERE chat_id = ?
            """,
            (1 if enabled else 0, utc_now(), int(chat_id)),
        )
        db.commit()


def remove_user(chat_id):
    clear_game_invites_for(chat_id)
    clear_pending_reports_related(chat_id)
    clear_user_social_graph(chat_id)
    with db_lock:
        db.execute("DELETE FROM subscribers WHERE chat_id = ?", (int(chat_id),))
        db.commit()


def has_user_consent(chat_id):
    with db_lock:
        row = db.execute("SELECT consent FROM subscribers WHERE chat_id = ?", (int(chat_id),)).fetchone()
    return bool(row and int(row["consent"]) == 1)


def is_user_registered(chat_id):
    row = get_user(chat_id)
    if not row:
        return False
    return bool(int(row.get("consent") or 0) == 1 and (row.get("registration_name") or "").strip())


def row_to_dict(row):
    return dict(row) if row else None


def get_user(chat_id):
    clear_expired_bans()
    with db_lock:
        row = db.execute(
            """
            SELECT chat_id, username, first_name, last_name, language_code, is_premium, is_bot,
                   consent, consent_at, broadcast_enabled, registration_name, registered_at,
                   class_group, allow_friend_requests, searchable_by_name,
                   visit_count, last_visit_at, is_banned, ban_reason, ban_until, subscribed_at, last_seen_at,
                   last_message_text, last_message_at, total_messages, calc_success_count,
                   calc_failed_count, relayed_count, game_wins, game_losses, game_draws, game_points,
                   last_calc_input, last_calc_output
            FROM subscribers
            WHERE chat_id = ?
            """,
            (int(chat_id),),
        ).fetchone()
    return row_to_dict(row)


def count_users(consent_only=False):
    clear_expired_bans()
    with db_lock:
        if consent_only:
            row = db.execute("SELECT COUNT(*) AS c FROM subscribers WHERE consent = 1").fetchone()
        else:
            row = db.execute("SELECT COUNT(*) AS c FROM subscribers").fetchone()
    return int(row["c"] if row else 0)


def list_users(limit=50, offset=0, consent_only=False):
    clear_expired_bans()
    with db_lock:
        if consent_only:
            rows = db.execute(
                """
                SELECT chat_id, username, first_name, last_name, consent, broadcast_enabled, is_banned,
                       registration_name, class_group, visit_count, last_visit_at, last_seen_at
                FROM subscribers
                WHERE consent = 1
                ORDER BY COALESCE(last_seen_at, subscribed_at) DESC
                LIMIT ? OFFSET ?
                """,
                (int(limit), int(offset)),
            ).fetchall()
        else:
            rows = db.execute(
                """
                SELECT chat_id, username, first_name, last_name, consent, broadcast_enabled, is_banned,
                       registration_name, class_group, visit_count, last_visit_at, last_seen_at
                FROM subscribers
                ORDER BY COALESCE(last_seen_at, subscribed_at) DESC
                LIMIT ? OFFSET ?
                """,
                (int(limit), int(offset)),
            ).fetchall()
    return [dict(row) for row in rows]


def find_user_by_username(username):
    clear_expired_bans()
    normalized = username.strip().lstrip("@").lower()
    if not normalized:
        return None
    with db_lock:
        row = db.execute(
            """
            SELECT chat_id, username, first_name, last_name, language_code, is_premium, is_bot,
                   consent, consent_at, broadcast_enabled, registration_name, registered_at,
                   class_group, allow_friend_requests, searchable_by_name,
                   visit_count, last_visit_at, is_banned, ban_reason, ban_until, subscribed_at, last_seen_at,
                   last_message_text, last_message_at, total_messages, calc_success_count,
                   calc_failed_count, relayed_count, game_wins, game_losses, game_draws, game_points,
                   last_calc_input, last_calc_output
            FROM subscribers
            WHERE lower(username) = ?
            """,
            (normalized,),
        ).fetchone()
        if row:
            return row_to_dict(row)

        row = db.execute(
            """
            SELECT chat_id, username, first_name, last_name, language_code, is_premium, is_bot,
                   consent, consent_at, broadcast_enabled, registration_name, registered_at,
                   class_group, allow_friend_requests, searchable_by_name,
                   visit_count, last_visit_at, is_banned, ban_reason, ban_until, subscribed_at, last_seen_at,
                   last_message_text, last_message_at, total_messages, calc_success_count,
                   calc_failed_count, relayed_count, game_wins, game_losses, game_draws, game_points,
                   last_calc_input, last_calc_output
            FROM subscribers
            WHERE username IS NOT NULL AND lower(username) LIKE ?
            ORDER BY COALESCE(last_seen_at, subscribed_at) DESC
            LIMIT 1
            """,
            (f"%{normalized}%",),
        ).fetchone()
    return row_to_dict(row)


def find_friend_target(query, requester_id):
    clear_expired_bans()
    token = (query or "").strip()
    if not token:
        return None
    requester = int(requester_id)
    lowered = token.lstrip("@").lower()
    if lowered:
        with db_lock:
            row = db.execute(
                """
                SELECT chat_id, username, first_name, last_name, registration_name,
                       consent, is_banned, allow_friend_requests, searchable_by_name
                FROM subscribers
                WHERE chat_id != ?
                  AND consent = 1
                  AND is_banned = 0
                  AND username IS NOT NULL
                  AND lower(username) = ?
                LIMIT 1
                """,
                (requester, lowered),
            ).fetchone()
        if row:
            return row_to_dict(row)

    normalized_name = normalize_registration_name(token).lower()
    if not normalized_name:
        return None
    with db_lock:
        row = db.execute(
            """
            SELECT chat_id, username, first_name, last_name, registration_name,
                   consent, is_banned, allow_friend_requests, searchable_by_name
            FROM subscribers
            WHERE chat_id != ?
              AND consent = 1
              AND is_banned = 0
              AND searchable_by_name = 1
              AND registration_name IS NOT NULL
              AND lower(trim(registration_name)) = ?
            LIMIT 1
            """,
            (requester, normalized_name),
        ).fetchone()
    return row_to_dict(row)


def resolve_user_identifier(raw_value):
    token = (raw_value or "").strip()
    if not token:
        return None
    chat_id = parse_chat_id(token)
    if chat_id is not None:
        return get_user(chat_id)
    return find_user_by_username(token)


def get_stats():
    clear_expired_bans()
    with db_lock:
        row = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN consent = 1 THEN 1 ELSE 0 END) AS consented,
                SUM(CASE WHEN consent = 1 AND broadcast_enabled = 1 THEN 1 ELSE 0 END) AS broadcast_on,
                SUM(CASE WHEN consent = 1 AND broadcast_enabled = 0 THEN 1 ELSE 0 END) AS broadcast_off,
                SUM(CASE WHEN is_banned = 1 THEN 1 ELSE 0 END) AS banned_count,
                SUM(visit_count) AS visit_count,
                SUM(total_messages) AS total_messages,
                SUM(calc_success_count) AS calc_success_count,
                SUM(calc_failed_count) AS calc_failed_count,
                SUM(relayed_count) AS relayed_count,
                SUM(game_wins) AS game_wins,
                SUM(game_losses) AS game_losses,
                SUM(game_draws) AS game_draws,
                SUM(game_points) AS game_points
            FROM subscribers
            """
        ).fetchone()
    return {
        "total": int(row["total"] or 0),
        "consented": int(row["consented"] or 0),
        "broadcast_on": int(row["broadcast_on"] or 0),
        "broadcast_off": int(row["broadcast_off"] or 0),
        "banned_count": int(row["banned_count"] or 0),
        "visit_count": int(row["visit_count"] or 0),
        "total_messages": int(row["total_messages"] or 0),
        "calc_success_count": int(row["calc_success_count"] or 0),
        "calc_failed_count": int(row["calc_failed_count"] or 0),
        "relayed_count": int(row["relayed_count"] or 0),
        "game_wins": int(row["game_wins"] or 0),
        "game_losses": int(row["game_losses"] or 0),
        "game_draws": int(row["game_draws"] or 0),
        "game_points": int(row["game_points"] or 0),
    }


def log_registration_event(chat_id, registration_name):
    with db_lock:
        db.execute(
            """
            INSERT INTO registration_events(chat_id, registration_name, registered_at)
            VALUES(?, ?, ?)
            """,
            (int(chat_id), normalize_registration_name(registration_name), utc_now()),
        )
        db.commit()


def count_registration_events():
    with db_lock:
        row = db.execute("SELECT COUNT(*) AS c FROM registration_events").fetchone()
    return int(row["c"] if row else 0)


def list_registration_events(limit=20, offset=0):
    with db_lock:
        rows = db.execute(
            """
            SELECT re.id, re.chat_id, re.registration_name, re.registered_at,
                   s.username, s.first_name, s.last_name
            FROM registration_events re
            LEFT JOIN subscribers s ON s.chat_id = re.chat_id
            ORDER BY re.id DESC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        ).fetchall()
    return [dict(row) for row in rows]


def create_player_report(reporter_id, target_id, reason):
    now = utc_now()
    with db_lock:
        cursor = db.execute(
            """
            INSERT INTO player_reports(reporter_id, target_id, reason, status, created_at)
            VALUES(?, ?, ?, 'open', ?)
            """,
            (int(reporter_id), int(target_id), (reason or "").strip()[:REPORT_REASON_MAX_LEN], now),
        )
        db.commit()
    return int(cursor.lastrowid)


def count_player_reports(open_only=True):
    with db_lock:
        if open_only:
            row = db.execute("SELECT COUNT(*) AS c FROM player_reports WHERE status = 'open'").fetchone()
        else:
            row = db.execute("SELECT COUNT(*) AS c FROM player_reports").fetchone()
    return int(row["c"] if row else 0)


def list_player_reports(limit=20, offset=0, open_only=True):
    where_clause = "WHERE r.status = 'open'" if open_only else ""
    with db_lock:
        rows = db.execute(
            f"""
            SELECT r.id, r.reporter_id, r.target_id, r.reason, r.status, r.created_at, r.resolved_at,
                   sr.username AS reporter_username, sr.first_name AS reporter_first_name, sr.last_name AS reporter_last_name, sr.registration_name AS reporter_registration_name,
                   st.username AS target_username, st.first_name AS target_first_name, st.last_name AS target_last_name, st.registration_name AS target_registration_name
            FROM player_reports r
            LEFT JOIN subscribers sr ON sr.chat_id = r.reporter_id
            LEFT JOIN subscribers st ON st.chat_id = r.target_id
            {where_clause}
            ORDER BY r.id DESC
            LIMIT ? OFFSET ?
            """,
            (int(limit), int(offset)),
        ).fetchall()
    return [dict(row) for row in rows]


def get_player_report(report_id):
    with db_lock:
        row = db.execute(
            """
            SELECT r.id, r.reporter_id, r.target_id, r.reason, r.status, r.created_at, r.resolved_at,
                   sr.username AS reporter_username, sr.first_name AS reporter_first_name, sr.last_name AS reporter_last_name, sr.registration_name AS reporter_registration_name,
                   st.username AS target_username, st.first_name AS target_first_name, st.last_name AS target_last_name, st.registration_name AS target_registration_name
            FROM player_reports r
            LEFT JOIN subscribers sr ON sr.chat_id = r.reporter_id
            LEFT JOIN subscribers st ON st.chat_id = r.target_id
            WHERE r.id = ?
            LIMIT 1
            """,
            (int(report_id),),
        ).fetchone()
    return row_to_dict(row)


def close_player_report(report_id):
    with db_lock:
        cursor = db.execute(
            """
            UPDATE player_reports
            SET status = 'closed',
                resolved_at = ?
            WHERE id = ? AND status = 'open'
            """,
            (utc_now(), int(report_id)),
        )
        db.commit()
    return int(cursor.rowcount) > 0


def get_broadcast_targets():
    clear_expired_bans()
    with db_lock:
        rows = db.execute(
            """
            SELECT chat_id
            FROM subscribers
            WHERE consent = 1 AND broadcast_enabled = 1 AND is_banned = 0
            ORDER BY subscribed_at ASC
            """
        ).fetchall()
    return [int(row["chat_id"]) for row in rows]


def parse_chat_ids(token):
    result = []
    seen = set()
    for piece in token.split(","):
        value = piece.strip()
        if not value:
            continue
        chat_id = parse_chat_id(value)
        if chat_id is None or chat_id in seen:
            continue
        seen.add(chat_id)
        result.append(chat_id)
    return result


def parse_target_identifiers_csv(token):
    targets = []
    unresolved = []
    seen = set()
    for piece in token.split(","):
        value = piece.strip()
        if not value:
            continue
        user_row = resolve_user_identifier(value)
        if not user_row:
            unresolved.append(value)
            continue
        chat_id = int(user_row["chat_id"])
        if chat_id in seen:
            continue
        seen.add(chat_id)
        targets.append(chat_id)
    return targets, unresolved


def parse_two_user_identifiers(text):
    parts = (text or "").split()
    if len(parts) < 2:
        return None, None
    left = resolve_user_identifier(parts[0])
    right = resolve_user_identifier(parts[1])
    if not left or not right:
        return None, None
    return left, right


def reset_runtime_state_for_user(chat_id):
    queue_remove_player(chat_id)
    leave_or_forfeit_game(chat_id)
    clear_game_invites_for(chat_id)
    clear_pending_reports_related(chat_id)
    clear_receiver_registration(chat_id)
    clear_receiver_mode(chat_id)


def notify_removed_account(chat_id):
    try:
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Твой аккаунт удален администратором. Для нового входа используй /start.",
            reply_markup=remove_reply_keyboard(),
        )
    except Exception:  # noqa: BLE001
        pass


def try_notify_ban(chat_id, until_display=None):
    if until_display:
        text = f"Доступ временно ограничен администратором до {until_display}."
    else:
        text = "Доступ ограничен администратором."
    try:
        send_text(RECEIVER_BOT_TOKEN, chat_id, text, reply_markup=remove_reply_keyboard())
    except Exception:  # noqa: BLE001
        pass


def tg_api(token, method, params=None, timeout=POLL_TIMEOUT + 10):
    if params is None:
        params = {}
    url = f"https://api.telegram.org/bot{token}/{method}"
    payload = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
            response_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise TelegramApiError(exc.code, body) from exc
    data = json.loads(response_text)
    if not data.get("ok"):
        raise TelegramApiError(data.get("error_code"), data.get("description", "Telegram API error"))
    return data.get("result")


def send_text(token, chat_id, text, reply_markup=None):
    params = {
        "chat_id": int(chat_id),
        "text": text,
    }
    if reply_markup is not None:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    result = tg_api(token, "sendMessage", params)
    if token == SENDER_BOT_TOKEN:
        message_id = result.get("message_id") if isinstance(result, dict) else None
        if message_id is not None:
            log_admin_message(chat_id, int(message_id))
        try:
            maybe_cleanup_admin_chat(chat_id, limit=60)
        except Exception:  # noqa: BLE001
            pass
    return result


def edit_text(token, chat_id, message_id, text, reply_markup=None):
    params = {
        "chat_id": int(chat_id),
        "message_id": int(message_id),
        "text": text,
    }
    if reply_markup is not None:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return tg_api(token, "editMessageText", params)


def delete_message(token, chat_id, message_id):
    try:
        return tg_api(
            token,
            "deleteMessage",
            {
                "chat_id": int(chat_id),
                "message_id": int(message_id),
            },
        )
    except TelegramApiError:
        return None


def receiver_edit_or_send(chat_id, message_id, text, reply_markup=None):
    try:
        edit_text(RECEIVER_BOT_TOKEN, chat_id, message_id, text, reply_markup=reply_markup)
    except TelegramApiError:
        send_text(RECEIVER_BOT_TOKEN, chat_id, text, reply_markup=reply_markup)


def answer_callback(token, callback_id, text=None, show_alert=False):
    params = {"callback_query_id": callback_id}
    if text:
        params["text"] = text
    if show_alert:
        params["show_alert"] = True
    return tg_api(token, "answerCallbackQuery", params)


def get_updates(token, offset, allowed_updates):
    return tg_api(
        token,
        "getUpdates",
        {
            "offset": offset,
            "timeout": POLL_TIMEOUT,
            "allowed_updates": json.dumps(allowed_updates),
        },
        timeout=POLL_TIMEOUT + 15,
    )


def is_command(text, command):
    if not text:
        return False
    return text.split("@")[0].startswith(command)


def split_command(text):
    if not text.startswith("/"):
        return "", text
    parts = text.split(maxsplit=1)
    command = parts[0].split("@")[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    return command, args


def build_name(user_row):
    parts = []
    first_name = user_row.get("first_name")
    last_name = user_row.get("last_name")
    username = user_row.get("username")
    registration_name = user_row.get("registration_name")
    if first_name:
        parts.append(first_name)
    if last_name:
        parts.append(last_name)
    if not parts and registration_name:
        parts.append(str(registration_name))
    name = " ".join(parts).strip()
    if username:
        return f"{name} (@{username})" if name else f"@{username}"
    if name:
        return name
    return str(user_row.get("chat_id"))


def short_user_line(user_row):
    consent_text = "yes" if int(user_row.get("consent") or 0) == 1 else "no"
    broadcast_text = "on" if int(user_row.get("broadcast_enabled") or 0) == 1 else "off"
    banned_text = "yes" if int(user_row.get("is_banned") or 0) == 1 else "no"
    reg_name = user_row.get("registration_name") or "-"
    last_seen = user_row.get("last_seen_at") or "-"
    return (
        f"{user_row.get('chat_id')} | {build_name(user_row)} | "
        f"reg:{consent_text} | broadcast:{broadcast_text} | banned:{banned_text} | reg_name:{reg_name} | seen:{last_seen}"
    )


def user_detail(user_row):
    username = user_row.get("username")
    profile_link = f"https://t.me/{username}" if username else "-"
    calc_success = int(user_row.get("calc_success_count") or 0)
    calc_failed = int(user_row.get("calc_failed_count") or 0)
    total_calc = calc_success + calc_failed
    success_rate = f"{(calc_success / total_calc) * 100:.1f}%" if total_calc else "-"
    row_chat_id = user_row.get("chat_id")
    friends_total = count_friends(row_chat_id) if row_chat_id is not None else 0
    lines = [
        f"ID: {user_row.get('chat_id')}",
        f"Имя: {build_name(user_row)}",
        f"Регистрация (имя): {user_row.get('registration_name') or '-'}",
        f"Username: @{username}" if username else "Username: -",
        f"Профиль: {profile_link}",
        f"language_code: {user_row.get('language_code') or '-'}",
        f"is_premium: {int(user_row.get('is_premium') or 0)}",
        f"is_bot: {int(user_row.get('is_bot') or 0)}",
        f"registered: {int(user_row.get('consent') or 0)}",
        f"registered_at: {user_row.get('registered_at') or user_row.get('consent_at') or '-'}",
        f"class_group: {user_row.get('class_group') or '5-8'}",
        f"allow_friend_requests: {int(user_row.get('allow_friend_requests') or 0)}",
        f"searchable_by_name: {int(user_row.get('searchable_by_name') or 0)}",
        f"friends_count: {friends_total}",
        f"visit_count: {int(user_row.get('visit_count') or 0)}",
        f"last_visit_at: {user_row.get('last_visit_at') or '-'}",
        f"broadcast_enabled: {int(user_row.get('broadcast_enabled') or 0)}",
        f"is_banned: {int(user_row.get('is_banned') or 0)}",
        f"ban_reason: {user_row.get('ban_reason') or '-'}",
        f"ban_until: {format_local_timestamp(user_row.get('ban_until')) if user_row.get('ban_until') else '-'}",
        f"subscribed_at: {user_row.get('subscribed_at') or '-'}",
        f"last_seen_at: {user_row.get('last_seen_at') or '-'}",
        f"last_message_at: {user_row.get('last_message_at') or '-'}",
        f"last_message_text: {user_row.get('last_message_text') or '-'}",
        f"total_messages: {int(user_row.get('total_messages') or 0)}",
        f"calc_success_count: {calc_success}",
        f"calc_failed_count: {calc_failed}",
        f"calc_success_rate: {success_rate}",
        f"relayed_count: {int(user_row.get('relayed_count') or 0)}",
        f"game_wins: {int(user_row.get('game_wins') or 0)}",
        f"game_losses: {int(user_row.get('game_losses') or 0)}",
        f"game_draws: {int(user_row.get('game_draws') or 0)}",
        f"game_points: {int(user_row.get('game_points') or 0)}",
        f"last_calc_input: {user_row.get('last_calc_input') or '-'}",
        f"last_calc_output: {user_row.get('last_calc_output') or '-'}",
    ]
    return "\n".join(lines)


def user_stats_text(user_row):
    calc_success = int(user_row.get("calc_success_count") or 0)
    calc_failed = int(user_row.get("calc_failed_count") or 0)
    total_calc = calc_success + calc_failed
    success_rate = f"{(calc_success / total_calc) * 100:.1f}%" if total_calc else "-"
    row_chat_id = user_row.get("chat_id")
    friends_total = count_friends(row_chat_id) if row_chat_id is not None else 0
    return "\n".join(
        [
            f"Статистика пользователя: {build_name(user_row)}",
            f"ID: {user_row.get('chat_id')}",
            f"Класс/уровень: {user_row.get('class_group') or '5-8'}",
            f"Друзей: {friends_total}",
            f"Посещений: {int(user_row.get('visit_count') or 0)}",
            f"last_visit_at: {user_row.get('last_visit_at') or '-'}",
            f"Всего сообщений: {int(user_row.get('total_messages') or 0)}",
            f"Успешных вычислений: {calc_success}",
            f"Ошибок вычислений: {calc_failed}",
            f"Успешность: {success_rate}",
            f"Передано админу: {int(user_row.get('relayed_count') or 0)}",
            f"Игр: W{int(user_row.get('game_wins') or 0)} / L{int(user_row.get('game_losses') or 0)} / D{int(user_row.get('game_draws') or 0)}",
            f"Игровые очки: {int(user_row.get('game_points') or 0)}",
            f"Последний ввод: {user_row.get('last_calc_input') or '-'}",
            f"Последний ответ: {user_row.get('last_calc_output') or '-'}",
            f"last_seen_at: {user_row.get('last_seen_at') or '-'}",
            f"broadcast_enabled: {int(user_row.get('broadcast_enabled') or 0)}",
            f"is_banned: {int(user_row.get('is_banned') or 0)}",
            f"ban_until: {format_local_timestamp(user_row.get('ban_until')) if user_row.get('ban_until') else '-'}",
        ]
    )


def get_top_users(limit=10):
    with db_lock:
        rows = db.execute(
            """
            SELECT chat_id, username, first_name, last_name, registration_name, total_messages,
                   calc_success_count, calc_failed_count, relayed_count, is_banned,
                   game_points, game_wins, game_losses, game_draws, visit_count
            FROM subscribers
            ORDER BY game_points DESC, total_messages DESC, COALESCE(last_seen_at, subscribed_at) DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def mode_text():
    state = get_admin_mode()
    mode = state.get("type")
    if not mode:
        return "режим: обычный"
    if mode == "broadcast_all":
        return "режим: ожидание текста для рассылки"
    if mode == "pick_direct":
        return "режим: ожидание id/@username"
    if mode == "compose_direct":
        return f"режим: ожидание текста пользователю {state.get('target_id')}"
    if mode == "pick_targets":
        return "режим: ожидание списка получателей (id/@username через запятую)"
    if mode == "compose_targets":
        return f"режим: ожидание текста для выбранных ({len(state.get('target_ids') or [])})"
    if mode == "find_user":
        return "режим: поиск пользователя по id/@username"
    if mode == "rename_user":
        return f"режим: смена имени пользователю {state.get('target_id')}"
    if mode == "ban_for_user":
        return f"режим: временный бан пользователю {state.get('target_id')}"
    if mode == "add_friend_for_user":
        return f"режим: добавить друга пользователю {state.get('target_id')}"
    return f"режим: {mode}"


def admin_help_text():
    return (
        "Вход в админ-панель: /start -> пароль 3 раза.\n\n"
        "Админ-команды:\n"
        "/panel или /status - панель\n"
        "/users - список пользователей (первые 8 + кнопки)\n"
        "/users all - текстовый список\n"
        "/user <id|@username> - подробные данные\n"
        "/user_regs <id|@username> - история регистраций пользователя\n"
        "/ban <id|@username> - заблокировать пользователя\n"
        "/unban <id|@username> - снять блокировку\n"
        "/mute <id|@username> - выключить рассылку\n"
        "/unmute <id|@username> - включить рассылку\n"
        "/remove <id|@username> - удалить из базы\n"
        "/send <id|@username> <текст> - отправить одному\n"
        "/top - топ активных пользователей\n"
        "/setname <id|@username> <имя> - сменить имя регистрации\n"
        "/friend_add <id|@u> <id|@u> - добавить в друзья\n"
        "/friend_remove <id|@u> <id|@u> - удалить дружбу\n"
        "/ban_for <id|@u> <время> - временный бан (1h, 12h, 1d, 12:00)\n"
        "/reports - открытые жалобы\n"
        "/registrations - журнал регистраций\n"
        "/autoclean <off|10m|1h|12h|1d> - автоочистка чата админа\n"
        "/broadcast <текст> - рассылка всем активным\n"
        "/broadcast_to <id|@user,id|@user> <текст> - выборочная рассылка\n"
        "/cancel - отмена текущего режима\n"
        "/help - помощь"
    )


def admin_panel_text():
    stats = get_stats()
    reports_open = count_player_reports(open_only=True)
    registrations_total = count_registration_events()
    autoclean_value = get_admin_autoclean_seconds()
    recent = list_users(limit=6, offset=0, consent_only=True)
    lines = [
        "Админ-панель",
        mode_text(),
        "",
        f"Всего в базе: {stats['total']}",
        f"Зарегистрировано: {stats['consented']}",
        f"Рассылка включена: {stats['broadcast_on']}",
        f"Рассылка выключена: {stats['broadcast_off']}",
        f"Заблокировано: {stats['banned_count']}",
        f"Посещений (суммарно): {stats['visit_count']}",
        f"Всего сообщений от пользователей: {stats['total_messages']}",
        f"Успешных вычислений: {stats['calc_success_count']}",
        f"Ошибок вычислений: {stats['calc_failed_count']}",
        f"Передано админу: {stats['relayed_count']}",
        f"Игр W/L/D: {stats['game_wins']}/{stats['game_losses']}/{stats['game_draws']}",
        f"Игровые очки: {stats['game_points']}",
        f"Открытых жалоб: {reports_open}",
        f"Событий регистрации: {registrations_total}",
        f"Автоочистка чата админа: {format_duration(autoclean_value)}",
        "",
        "Последние пользователи:",
    ]
    if recent:
        for row in recent:
            lines.append(short_user_line(row))
    else:
        lines.append("Нет пользователей.")
    return "\n".join(lines)


def admin_main_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "Статистика", "callback_data": "adm:stats"},
                {"text": "Пользователи", "callback_data": "adm:users:0"},
            ],
            [
                {"text": "Жалобы", "callback_data": "adm:reports:0"},
                {"text": "Регистрации", "callback_data": "adm:registrations:0"},
            ],
            [
                {"text": "Рассылка всем", "callback_data": "adm:broadcast_all"},
                {"text": "Рассылка выборочно", "callback_data": "adm:pick_targets"},
            ],
            [
                {"text": "Рассылка одному", "callback_data": "adm:pick_direct"},
                {"text": "Найти по нику", "callback_data": "adm:find_user"},
            ],
            [
                {"text": "Топ активных", "callback_data": "adm:top"},
                {"text": "Обновить", "callback_data": "adm:panel"},
            ],
            [
                {"text": "Автоочистка", "callback_data": "adm:autoclean_menu"},
            ],
        ]
    }


def admin_cancel_keyboard():
    return {"inline_keyboard": [[{"text": "Отмена", "callback_data": "adm:cancel_mode"}]]}


def admin_autoclean_text():
    current = get_admin_autoclean_seconds()
    return (
        "Автоочистка сообщений админ-бота.\n"
        f"Текущее значение: {format_duration(current)}\n"
        "Выбери интервал очистки или выключи."
    )


def admin_autoclean_keyboard():
    current = get_admin_autoclean_seconds()
    options = [
        ("Выключено", 0),
        ("10 минут", 600),
        ("1 час", 3600),
        ("6 часов", 21600),
        ("12 часов", 43200),
        ("1 день", 86400),
    ]
    rows = []
    for label, seconds in options:
        marker = "✅ " if int(seconds) == int(current) else ""
        rows.append([{"text": f"{marker}{label}", "callback_data": f"adm:autoclean_set:{seconds}"}])
    rows.append([{"text": "Меню", "callback_data": "adm:panel"}])
    return {"inline_keyboard": rows}


def build_user_keyboard(user_row, offset):
    chat_id = int(user_row["chat_id"])
    broadcast_on = int(user_row.get("broadcast_enabled") or 0) == 1
    banned = int(user_row.get("is_banned") or 0) == 1
    mute_text = "Выкл рассылку" if broadcast_on else "Вкл рассылку"
    mute_action = "mute" if broadcast_on else "unmute"
    ban_text = "Разбан" if banned else "Бан"
    ban_action = "unban" if banned else "ban"
    return {
        "inline_keyboard": [
            [
                {"text": "Данные", "callback_data": f"adm:userdata:{chat_id}:{offset}"},
                {"text": "Статистика", "callback_data": f"adm:userstats:{chat_id}:{offset}"},
            ],
            [
                {"text": mute_text, "callback_data": f"adm:{mute_action}:{chat_id}:{offset}"},
                {"text": ban_text, "callback_data": f"adm:{ban_action}:{chat_id}:{offset}"},
            ],
            [
                {"text": "Написать", "callback_data": f"adm:compose:{chat_id}"},
                {"text": "Удалить", "callback_data": f"adm:remove:{chat_id}:{offset}"},
            ],
            [
                {"text": "Сменить имя", "callback_data": f"adm:rename:{chat_id}"},
                {"text": "Добавить друга", "callback_data": f"adm:addfriend:{chat_id}"},
            ],
            [
                {"text": "Бан на время", "callback_data": f"adm:banfor:{chat_id}"},
            ],
            [
                {"text": "Регистрации", "callback_data": f"adm:userregs:{chat_id}:{offset}"},
            ],
            [{"text": "Назад", "callback_data": f"adm:users:{offset}"}],
            [{"text": "Меню", "callback_data": "adm:panel"}],
        ]
    }


def build_users_page(offset):
    total = count_users(consent_only=True)
    safe_offset = max(0, int(offset))
    if safe_offset >= total and total > 0:
        safe_offset = max(total - PAGE_SIZE, 0)
    rows = list_users(limit=PAGE_SIZE, offset=safe_offset, consent_only=True)
    lines = [f"Пользователи {safe_offset + 1}-{safe_offset + len(rows)} из {total}:"]
    if not rows:
        lines.append("Список пуст.")
    for row in rows:
        lines.append(short_user_line(row))

    keyboard_rows = []
    for row in rows:
        title = build_name(row)
        if len(title) > 28:
            title = f"{title[:25]}..."
        keyboard_rows.append(
            [{"text": title, "callback_data": f"adm:user:{int(row['chat_id'])}:{safe_offset}"}]
        )

    nav_row = []
    if safe_offset > 0:
        prev_offset = max(0, safe_offset - PAGE_SIZE)
        nav_row.append({"text": "⬅", "callback_data": f"adm:users:{prev_offset}"})
    if safe_offset + PAGE_SIZE < total:
        next_offset = safe_offset + PAGE_SIZE
        nav_row.append({"text": "➡", "callback_data": f"adm:users:{next_offset}"})
    if nav_row:
        keyboard_rows.append(nav_row)
    keyboard_rows.append([{"text": "Меню", "callback_data": "adm:panel"}])
    return "\n".join(lines), {"inline_keyboard": keyboard_rows}


def build_reports_page(offset):
    total = count_player_reports(open_only=True)
    safe_offset = max(0, int(offset))
    if safe_offset >= total and total > 0:
        safe_offset = max(total - PAGE_SIZE, 0)
    rows = list_player_reports(limit=PAGE_SIZE, offset=safe_offset, open_only=True)
    lines = [f"Открытые жалобы {safe_offset + 1}-{safe_offset + len(rows)} из {total}:"]
    if not rows:
        lines.append("Список пуст.")
    keyboard_rows = []
    for row in rows:
        report_id = int(row["id"])
        reporter = report_side_name(row, "reporter")
        target = report_side_name(row, "target")
        created = format_local_timestamp(row.get("created_at"))
        lines.append(f"#{report_id} | {reporter} -> {target} | {created}")
        title = trim_button_title(f"#{report_id} {reporter} -> {target}", max_len=40)
        keyboard_rows.append([{"text": title, "callback_data": f"adm:report:{report_id}:{safe_offset}"}])

    nav_row = []
    if safe_offset > 0:
        prev_offset = max(0, safe_offset - PAGE_SIZE)
        nav_row.append({"text": "⬅", "callback_data": f"adm:reports:{prev_offset}"})
    if safe_offset + PAGE_SIZE < total:
        next_offset = safe_offset + PAGE_SIZE
        nav_row.append({"text": "➡", "callback_data": f"adm:reports:{next_offset}"})
    if nav_row:
        keyboard_rows.append(nav_row)
    keyboard_rows.append([{"text": "Меню", "callback_data": "adm:panel"}])
    return "\n".join(lines), {"inline_keyboard": keyboard_rows}


def report_detail_text(report_row):
    if not report_row:
        return "Жалоба не найдена."
    status = report_row.get("status") or "-"
    resolved = format_local_timestamp(report_row.get("resolved_at")) if report_row.get("resolved_at") else "-"
    return "\n".join(
        [
            f"Жалоба #{int(report_row['id'])}",
            f"Статус: {status}",
            f"От: {report_side_name(report_row, 'reporter')} (id:{int(report_row['reporter_id'])})",
            f"На: {report_side_name(report_row, 'target')} (id:{int(report_row['target_id'])})",
            f"Когда: {format_local_timestamp(report_row.get('created_at'))}",
            f"Закрыта: {resolved}",
            f"Причина:\n{report_row.get('reason') or '-'}",
        ]
    )


def build_registrations_page(offset):
    total = count_registration_events()
    safe_offset = max(0, int(offset))
    if safe_offset >= total and total > 0:
        safe_offset = max(total - PAGE_SIZE, 0)
    rows = list_registration_events(limit=PAGE_SIZE, offset=safe_offset)
    lines = [f"Журнал регистраций {safe_offset + 1}-{safe_offset + len(rows)} из {total}:"]
    if not rows:
        lines.append("Список пуст.")
    for row in rows:
        profile_name = build_name(
            {
                "chat_id": row.get("chat_id"),
                "username": row.get("username"),
                "first_name": row.get("first_name"),
                "last_name": row.get("last_name"),
                "registration_name": row.get("registration_name"),
            }
        )
        lines.append(
            f"#{int(row['id'])} | id:{int(row['chat_id'])} | {profile_name} | reg_name:{row.get('registration_name') or '-'} | {format_local_timestamp(row.get('registered_at'))}"
        )

    nav_row = []
    if safe_offset > 0:
        prev_offset = max(0, safe_offset - PAGE_SIZE)
        nav_row.append({"text": "⬅", "callback_data": f"adm:registrations:{prev_offset}"})
    if safe_offset + PAGE_SIZE < total:
        next_offset = safe_offset + PAGE_SIZE
        nav_row.append({"text": "➡", "callback_data": f"adm:registrations:{next_offset}"})

    keyboard_rows = []
    if nav_row:
        keyboard_rows.append(nav_row)
    keyboard_rows.append([{"text": "Меню", "callback_data": "adm:panel"}])
    return "\n".join(lines), {"inline_keyboard": keyboard_rows}


def list_registration_events_for_user(chat_id, limit=20):
    with db_lock:
        rows = db.execute(
            """
            SELECT id, chat_id, registration_name, registered_at
            FROM registration_events
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(chat_id), int(limit)),
        ).fetchall()
    return [dict(row) for row in rows]


def user_registration_events_text(target_row):
    target_id = int(target_row["chat_id"])
    events = list_registration_events_for_user(target_id, limit=30)
    lines = [f"История регистраций: {build_name(target_row)}", f"ID: {target_id}"]
    if not events:
        lines.append("Событий регистрации не найдено.")
        return "\n".join(lines)
    lines.append(f"Всего событий: {len(events)} (последние):")
    for row in events:
        lines.append(
            f"#{int(row['id'])} | имя: {row.get('registration_name') or '-'} | {format_local_timestamp(row.get('registered_at'))}"
        )
    return "\n".join(lines)


def receiver_help_text():
    return (
        "Я бот-калькулятор.\n"
        "Если не понимаешь формат, напиши help или /help.\n"
        "Знаки: +  -  *  /  :  ×  ÷  ^\n"
        "Дробь: 1/2 или 1:2\n"
        "Умножение: 2*3, 2×3, 2(3+4)\n"
        "Степень: 2^10\n"
        "Функции: sin cos tan asin acos atan sqrt abs ln log log10 exp round floor ceil fact\n"
        "Примеры:\n"
        "2+2\n"
        "10:2\n"
        "2×(3+4)\n"
        "sin(pi/2)+sqrt(16)\n"
        "реши x^2-5*x+6=0\n"
        "Команды:\n"
        "/start - регистрация\n"
        "/privacy - какие данные о тебе хранятся\n"
        "/stop - сброс регистрации"
    )


def registration_prompt_text():
    return (
        "Я бот-калькулятор.\n"
        "Для начала работы нужна регистрация.\n"
        "Напиши свое имя одним сообщением.\n"
        "Если не понимаешь формат, напиши help."
    )


def receiver_main_keyboard():
    return {
        "keyboard": [
            [{"text": BTN_CALC}, {"text": BTN_HELP}],
            [{"text": BTN_STATS}, {"text": BTN_SETTINGS}],
            [{"text": BTN_ONLINE}, {"text": BTN_FRIENDS}],
            [{"text": BTN_HOME}],
        ],
        "resize_keyboard": True,
    }


def receiver_settings_keyboard(chat_id):
    row = get_user(chat_id) or {}
    current_class = row.get("class_group") or "5-8"
    allow_requests = int(row.get("allow_friend_requests") or 0) == 1
    searchable = int(row.get("searchable_by_name") or 0) == 1
    requests_text = "Входящие заявки: вкл" if allow_requests else "Входящие заявки: выкл"
    search_text = "Поиск по имени: вкл" if searchable else "Поиск по имени: выкл"
    return {
        "inline_keyboard": [
            [{"text": "Изменить имя", "callback_data": "rcv:set_name"}],
            [{"text": f"Класс: {current_class}", "callback_data": "rcv:set_class_menu"}],
            [{"text": requests_text, "callback_data": "rcv:toggle_friend_requests"}],
            [{"text": search_text, "callback_data": "rcv:toggle_searchable"}],
            [{"text": "Домой", "callback_data": "rcv:home"}],
        ]
    }


def receiver_class_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "1-4 класс", "callback_data": "rcv:set_class:1-4"},
                {"text": "5-8 класс", "callback_data": "rcv:set_class:5-8"},
            ],
            [
                {"text": "9-11 класс", "callback_data": "rcv:set_class:9-11"},
                {"text": "Продвинутый", "callback_data": "rcv:set_class:pro"},
            ],
            [{"text": "Домой", "callback_data": "rcv:home"}],
        ]
    }


def receiver_online_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "Искать соперника", "callback_data": "rcv:online_find"}],
            [{"text": "Правила", "callback_data": "rcv:online_rules"}],
            [{"text": "Домой", "callback_data": "rcv:home"}],
        ]
    }


def receiver_waiting_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "Отменить поиск", "callback_data": "rcv:online_cancel"}],
            [{"text": "Домой", "callback_data": "rcv:home"}],
        ]
    }


def receiver_game_ready_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "START", "callback_data": "rcv:game_start"}],
            [{"text": "Домой", "callback_data": "rcv:online_leave"}],
        ]
    }


def receiver_game_round_keyboard(opponent_id):
    return {
        "inline_keyboard": [
            [{"text": "🚩 Пожаловаться", "callback_data": f"rcv:report:{int(opponent_id)}"}],
            [{"text": "Домой", "callback_data": "rcv:online_leave"}],
        ]
    }


def remove_reply_keyboard():
    return {"remove_keyboard": True}


def receiver_friends_text(chat_id):
    friends_total = count_friends(chat_id)
    incoming_total = len(list_incoming_friend_requests(chat_id, limit=100))
    return (
        "Раздел друзей.\n"
        f"Друзей: {friends_total}\n"
        f"Входящих заявок: {incoming_total}\n"
        "Выбери действие:"
    )


def receiver_friends_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "➕ Добавить друга", "callback_data": "rcv:friend_add"}],
            [{"text": "📥 Входящие заявки", "callback_data": "rcv:friend_incoming"}],
            [{"text": "👥 Мои друзья", "callback_data": "rcv:friend_list"}],
            [{"text": "🏠 Домой", "callback_data": "rcv:home"}],
        ]
    }


def trim_button_title(title, max_len=30):
    text = (title or "").strip() or "Пользователь"
    return f"{text[: max_len - 3]}..." if len(text) > max_len else text


def receiver_incoming_requests_view(chat_id):
    rows = list_incoming_friend_requests(chat_id, limit=20)
    lines = ["Входящие заявки в друзья:"]
    keyboard_rows = []
    if not rows:
        lines.append("Список пуст.")
    else:
        for row in rows:
            requester_id = int(row["chat_id"])
            name = trim_button_title(build_name(row), max_len=25)
            lines.append(f"- {build_name(row)}")
            keyboard_rows.append(
                [
                    {"text": f"✅ {name}", "callback_data": f"rcv:fr_accept:{requester_id}"},
                    {"text": f"❌ {name}", "callback_data": f"rcv:fr_reject:{requester_id}"},
                ]
            )
    keyboard_rows.append([{"text": "⬅ Назад", "callback_data": "rcv:friends_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard_rows}


def receiver_friend_list_view(chat_id):
    rows = list_friends(chat_id, limit=40)
    lines = ["Мои друзья:"]
    keyboard_rows = []
    if not rows:
        lines.append("Пока нет друзей.")
    else:
        for row in rows:
            friend_id = int(row["chat_id"])
            label = trim_button_title(build_name(row), max_len=32)
            lines.append(f"- {build_name(row)}")
            keyboard_rows.append([{"text": label, "callback_data": f"rcv:friend_view:{friend_id}"}])
    keyboard_rows.append([{"text": "➕ Добавить друга", "callback_data": "rcv:friend_add"}])
    keyboard_rows.append([{"text": "⬅ Назад", "callback_data": "rcv:friends_menu"}])
    return "\n".join(lines), {"inline_keyboard": keyboard_rows}


def receiver_friend_actions_keyboard(friend_id):
    target = int(friend_id)
    return {
        "inline_keyboard": [
            [{"text": "🎮 Пригласить в дуэль", "callback_data": f"rcv:friend_invite:{target}"}],
            [{"text": "❌ Удалить из друзей", "callback_data": f"rcv:friend_remove:{target}"}],
            [{"text": "⬅ К списку", "callback_data": "rcv:friend_list"}],
        ]
    }


def receiver_invite_keyboard(inviter_id):
    inviter = int(inviter_id)
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Принять", "callback_data": f"rcv:invite_accept:{inviter}"},
                {"text": "❌ Отклонить", "callback_data": f"rcv:invite_decline:{inviter}"},
            ],
            [{"text": "🏠 Домой", "callback_data": "rcv:home"}],
        ]
    }


def receiver_friend_request_action_keyboard(requester_id):
    requester = int(requester_id)
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Принять", "callback_data": f"rcv:fr_accept:{requester}"},
                {"text": "❌ Отклонить", "callback_data": f"rcv:fr_reject:{requester}"},
            ],
            [{"text": "👥 Друзья", "callback_data": "rcv:friends_menu"}],
        ]
    }


def receiver_home_text():
    return "Выбери действие. Для подсказок по формулам: help"


def receiver_online_rules_text():
    return (
        "Онлайн-режим: дуэль по математике.\n"
        f"- {GAME_ROUNDS} раундов\n"
        f"- на каждый раунд {GAME_QUESTION_TIMEOUT} сек\n"
        "- кто первым даст правильный ответ, получает 1 очко\n"
        "- после раундов считаем победителя\n"
        "Нажми «Искать соперника»."
    )


def receiver_personal_stats_text(user_row):
    calc_success = int(user_row.get("calc_success_count") or 0)
    calc_failed = int(user_row.get("calc_failed_count") or 0)
    calc_total = calc_success + calc_failed
    calc_rate = f"{(calc_success / calc_total) * 100:.1f}%" if calc_total else "-"
    row_chat_id = user_row.get("chat_id")
    friends_total = count_friends(row_chat_id) if row_chat_id is not None else 0
    return "\n".join(
        [
            f"Твоя статистика: {build_name(user_row)}",
            f"Имя регистрации: {user_row.get('registration_name') or '-'}",
            f"Класс/уровень: {user_row.get('class_group') or '5-8'}",
            f"Посещений: {int(user_row.get('visit_count') or 0)}",
            f"Последний вход: {user_row.get('last_visit_at') or '-'}",
            f"Сообщений: {int(user_row.get('total_messages') or 0)}",
            f"Успешных вычислений: {calc_success}",
            f"Ошибок вычислений: {calc_failed}",
            f"Успешность: {calc_rate}",
            f"Игр W/L/D: {int(user_row.get('game_wins') or 0)}/{int(user_row.get('game_losses') or 0)}/{int(user_row.get('game_draws') or 0)}",
            f"Игровые очки: {int(user_row.get('game_points') or 0)}",
            f"Друзей: {friends_total}",
        ]
    )


def normalize_math_text(text):
    prepared = (text or "").strip()
    prepared = prepared.replace("÷", "/").replace("×", "*").replace("^", "**")
    prepared = prepared.replace("−", "-").replace("—", "-")
    prepared = re.sub(r"(?<![:/]):(?!/)", "/", prepared)
    prepared = prepared.replace("Х", "x").replace("х", "x").replace("X", "x")
    prepared = re.sub(r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)\s*(\()", r"\1*\2", prepared)
    prepared = re.sub(
        r"(?<![A-Za-z0-9_])(\d+(?:\.\d+)?)\s*(?=(sin|cos|tan|asin|acos|atan|sqrt|abs|ln|log10|log|exp|round|floor|ceil|fact|pi|e)\b)",
        r"\1*",
        prepared,
    )
    prepared = re.sub(r"(\))\s*(\()", r"\1*\2", prepared)
    prepared = re.sub(r"(\))\s*(\d)", r"\1*\2", prepared)
    prepared = re.sub(r"(\))\s*(x)", r"\1*\2", prepared)
    prepared = re.sub(r"(?<=\d)\s*x(?=\d|\()", "*", prepared)
    prepared = re.sub(r"(?<=\d)\s*x(?=[+\-*/)=]|$)", "*x", prepared)
    prepared = re.sub(r"(?<=x)\s*(?=\()", "*", prepared)
    prepared = re.sub(r"(?<=x)\s*(?=\d)", "*", prepared)
    lowered = prepared.lower()
    prefixes = ("реши", "посчитай", "вычисли", "calculate", "calc", "solve")
    for prefix in prefixes:
        needle = f"{prefix} "
        if lowered.startswith(needle):
            prepared = prepared[len(needle) :].strip()
            break
    return prepared


def ensure_finite(value):
    if not math.isfinite(value):
        raise CalcEvalError("Некорректный результат.")
    if abs(value) > 1e15:
        raise CalcEvalError("Слишком большое число.")
    return value


def format_number(value):
    value = float(value)
    if abs(value) < 1e-12:
        value = 0.0
    if value.is_integer():
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


def fn_factorial(value):
    rounded = round(value)
    if abs(value - rounded) > 1e-10 or rounded < 0 or rounded > 100:
        raise CalcEvalError("Факториал поддерживает только целые 0..100.")
    return float(math.factorial(int(rounded)))


def fn_log(value, base=math.e):
    return math.log(value, base)


ALLOWED_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

ALLOWED_FUNCTIONS = {
    "sin": (math.sin, 1, 1),
    "cos": (math.cos, 1, 1),
    "tan": (math.tan, 1, 1),
    "asin": (math.asin, 1, 1),
    "acos": (math.acos, 1, 1),
    "atan": (math.atan, 1, 1),
    "sqrt": (math.sqrt, 1, 1),
    "abs": (abs, 1, 1),
    "exp": (math.exp, 1, 1),
    "ln": (math.log, 1, 1),
    "log": (fn_log, 1, 2),
    "log10": (math.log10, 1, 1),
    "round": (round, 1, 2),
    "floor": (math.floor, 1, 1),
    "ceil": (math.ceil, 1, 1),
    "fact": (fn_factorial, 1, 1),
}


def safe_eval_node(node, x_value=None, depth=0):
    if depth > 40:
        raise CalcEvalError("Слишком сложное выражение.")

    if isinstance(node, ast.Expression):
        return safe_eval_node(node.body, x_value, depth + 1)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalcEvalError("Только числовые значения.")
        return float(node.value)

    if isinstance(node, ast.Name):
        identifier = node.id.lower()
        if identifier == "x":
            if x_value is None:
                raise CalcEvalError("Переменная x допустима только в уравнении.")
            return float(x_value)
        if identifier in ALLOWED_CONSTANTS:
            return float(ALLOWED_CONSTANTS[identifier])
        raise CalcEvalError("Неизвестная переменная.")

    if isinstance(node, ast.UnaryOp):
        operand = safe_eval_node(node.operand, x_value, depth + 1)
        if isinstance(node.op, ast.UAdd):
            return ensure_finite(+operand)
        if isinstance(node.op, ast.USub):
            return ensure_finite(-operand)
        raise CalcEvalError("Недопустимая операция.")

    if isinstance(node, ast.BinOp):
        left = safe_eval_node(node.left, x_value, depth + 1)
        right = safe_eval_node(node.right, x_value, depth + 1)
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.FloorDiv):
            result = left // right
        elif isinstance(node.op, ast.Mod):
            result = left % right
        elif isinstance(node.op, ast.Pow):
            if abs(right) > 12:
                raise CalcEvalError("Слишком большая степень.")
            result = left**right
        else:
            raise CalcEvalError("Недопустимая операция.")
        return ensure_finite(float(result))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise CalcEvalError("Недопустимый вызов.")
        function_name = node.func.id.lower()
        if function_name not in ALLOWED_FUNCTIONS:
            raise CalcEvalError("Функция не поддерживается.")
        function, min_args, max_args = ALLOWED_FUNCTIONS[function_name]
        if not (min_args <= len(node.args) <= max_args):
            raise CalcEvalError("Неверное число аргументов.")
        if node.keywords:
            raise CalcEvalError("Именованные аргументы не поддерживаются.")
        args = [safe_eval_node(arg, x_value, depth + 1) for arg in node.args]
        try:
            result = function(*args)
        except (ValueError, OverflowError, ZeroDivisionError):
            raise CalcEvalError("Ошибка вычисления функции.") from None
        return ensure_finite(float(result))

    raise CalcEvalError("Недопустимое выражение.")


def safe_eval_expression(expr, x_value=None):
    if not expr or len(expr) > MAX_EXPR_LEN:
        raise CalcEvalError("Слишком длинное выражение.")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise CalcEvalError("Синтаксическая ошибка.") from None
    return safe_eval_node(tree, x_value=x_value)


def poly_add(left, right):
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def poly_sub(left, right):
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def poly_mul(left, right):
    coeff = [0.0] * 5
    for i, lv in enumerate(left):
        for j, rv in enumerate(right):
            coeff[i + j] += lv * rv
    if abs(coeff[3]) > 1e-10 or abs(coeff[4]) > 1e-10:
        return None
    return (coeff[0], coeff[1], coeff[2])


def poly_pow(base, exponent):
    if exponent == 0:
        return (1.0, 0.0, 0.0)
    if exponent == 1:
        return base
    if exponent == 2:
        return poly_mul(base, base)
    return None


def poly_from_node(node, depth=0):
    if depth > 25:
        return None

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            return None
        return (float(node.value), 0.0, 0.0)

    if isinstance(node, ast.Name):
        identifier = node.id.lower()
        if identifier == "x":
            return (0.0, 1.0, 0.0)
        if identifier in ALLOWED_CONSTANTS:
            return (float(ALLOWED_CONSTANTS[identifier]), 0.0, 0.0)
        return None

    if isinstance(node, ast.UnaryOp):
        inner = poly_from_node(node.operand, depth + 1)
        if inner is None:
            return None
        if isinstance(node.op, ast.UAdd):
            return inner
        if isinstance(node.op, ast.USub):
            return (-inner[0], -inner[1], -inner[2])
        return None

    if isinstance(node, ast.BinOp):
        left = poly_from_node(node.left, depth + 1)
        right = poly_from_node(node.right, depth + 1)

        if isinstance(node.op, ast.Add):
            if left is None or right is None:
                return None
            return poly_add(left, right)

        if isinstance(node.op, ast.Sub):
            if left is None or right is None:
                return None
            return poly_sub(left, right)

        if isinstance(node.op, ast.Mult):
            if left is None or right is None:
                return None
            return poly_mul(left, right)

        if isinstance(node.op, ast.Pow):
            if left is None:
                return None
            if not isinstance(node.right, ast.Constant) or not isinstance(node.right.value, (int, float)):
                return None
            exponent = int(node.right.value)
            if abs(node.right.value - exponent) > 1e-10:
                return None
            return poly_pow(left, exponent)

    return None


def solve_polynomial_equation(left_expr, right_expr):
    try:
        tree = ast.parse(f"({left_expr})-({right_expr})", mode="eval")
    except SyntaxError:
        return None
    coeff = poly_from_node(tree.body)
    if coeff is None:
        return None

    c0, c1, c2 = coeff
    eps = 1e-12

    if abs(c2) < eps:
        if abs(c1) < eps:
            if abs(c0) < eps:
                return "Бесконечно много решений."
            return "Решений нет."
        root = -c0 / c1
        return f"x = {format_number(root)}"

    d = c1 * c1 - 4.0 * c2 * c0
    if d < -eps:
        return "Реальных решений нет."
    if abs(d) <= eps:
        root = -c1 / (2.0 * c2)
        return f"x = {format_number(root)}"

    sqrt_d = math.sqrt(d)
    x1 = (-c1 - sqrt_d) / (2.0 * c2)
    x2 = (-c1 + sqrt_d) / (2.0 * c2)
    roots = sorted([x1, x2])
    return f"x1 = {format_number(roots[0])}\nx2 = {format_number(roots[1])}"


def dedupe_roots(values):
    result = []
    for value in sorted(values):
        if not result or abs(result[-1] - value) > 1e-5:
            result.append(value)
    return result


def solve_numerically(left_expr, right_expr):
    def func(x_value):
        left_val = safe_eval_expression(left_expr, x_value=x_value)
        right_val = safe_eval_expression(right_expr, x_value=x_value)
        return left_val - right_val

    roots = []
    x_min = -100.0
    x_max = 100.0
    step = 1.0
    x = x_min
    while x < x_max:
        x_next = x + step
        try:
            y1 = func(x)
            y2 = func(x_next)
        except CalcEvalError:
            x = x_next
            continue

        if abs(y1) < 1e-6:
            roots.append(x)
        if abs(y2) < 1e-6:
            roots.append(x_next)
        if y1 * y2 < 0:
            left = x
            right = x_next
            for _ in range(70):
                mid = (left + right) / 2.0
                y_mid = func(mid)
                if abs(y_mid) < 1e-8:
                    left = right = mid
                    break
                if y1 * y_mid <= 0:
                    right = mid
                    y2 = y_mid
                else:
                    left = mid
                    y1 = y_mid
            roots.append((left + right) / 2.0)
        x = x_next

    roots = dedupe_roots(roots)
    if not roots:
        raise CalcEvalError("Не удалось найти решение в диапазоне [-100, 100].")

    if len(roots) == 1:
        return f"x = {format_number(roots[0])}"

    lines = []
    for idx, value in enumerate(roots[:6], start=1):
        lines.append(f"x{idx} = {format_number(value)}")
    if len(roots) > 6:
        lines.append("... найдено больше корней, показаны первые 6")
    return "\n".join(lines)


def solve_equation(expression):
    if expression.count("=") != 1:
        raise CalcEvalError("Используй одно '=' в уравнении.")
    left_expr, right_expr = [part.strip() for part in expression.split("=", 1)]
    if not left_expr or not right_expr:
        raise CalcEvalError("Неполное уравнение.")

    poly_result = solve_polynomial_equation(left_expr, right_expr)
    if poly_result is not None:
        return poly_result
    return solve_numerically(left_expr, right_expr)


def solve_math_text(raw_text):
    expression = normalize_math_text(raw_text)
    if not expression:
        raise CalcEvalError("Пустой запрос.")
    if len(expression) > MAX_EXPR_LEN:
        raise CalcEvalError("Слишком длинный запрос.")

    lowered = expression.lower()
    if "=" in expression and "x" in lowered:
        return solve_equation(expression)

    value = safe_eval_expression(expression)
    return format_number(value)


def class_group_to_difficulty(class_group):
    mapping = {
        "1-4": 1,
        "5-8": 2,
        "9-11": 3,
        "pro": 4,
    }
    return mapping.get((class_group or "").strip(), 2)


def pick_game_class_group(left_group, right_group):
    candidates = [left_group or "5-8", right_group or "5-8"]
    best = max(candidates, key=class_group_to_difficulty)
    return best


def generate_game_question(class_group):
    difficulty = class_group_to_difficulty(class_group)
    if difficulty <= 1:
        a = random.randint(2, 30)
        b = random.randint(2, 30)
        op = random.choice(["+", "-", "*"])
        expression = f"{a} {op} {b}"
        if op == "+":
            answer = a + b
        elif op == "-":
            answer = a - b
        else:
            answer = a * b
        return f"Вычисли: {expression}", str(int(answer))

    if difficulty == 2:
        op = random.choice(["+", "-", "*", "/"])
        if op == "/":
            b = random.randint(2, 15)
            answer = random.randint(2, 25)
            a = b * answer
            expression = f"{a} / {b}"
            return f"Вычисли: {expression}", str(int(answer))
        a = random.randint(10, 99)
        b = random.randint(5, 50)
        expression = f"{a} {op} {b}"
        if op == "+":
            answer = a + b
        elif op == "-":
            answer = a - b
        else:
            answer = a * b
        return f"Вычисли: {expression}", str(int(answer))

    if difficulty == 3:
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        c = random.randint(1, 20)
        forms = [
            (f"({a} * {b}) + {c}", (a * b) + c),
            (f"{a}^2 + {b}", (a**2) + b),
            (f"({a} + {b}) * {c}", (a + b) * c),
        ]
        expression, answer = random.choice(forms)
        return f"Вычисли: {expression}", str(int(answer))

    a = random.randint(2, 12)
    b = random.randint(2, 12)
    c = random.randint(2, 10)
    forms = [
        (f"({a}^2 + {b}^2) - {c}", (a**2 + b**2) - c),
        (f"({a} * {b}) + ({c}^2)", (a * b) + (c**2)),
        (f"{a}^3 - ({b} * {c})", (a**3) - (b * c)),
    ]
    expression, answer = random.choice(forms)
    return f"Вычисли: {expression}", str(int(answer))


def parse_numeric_answer(raw_text):
    text = (raw_text or "").strip().replace(",", ".")
    if not text:
        return None
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if value.is_integer():
        return str(int(value))
    return str(value)


def get_or_create_game_session(player_a, player_b):
    global game_seq
    with receiver_game_lock:
        game_seq += 1
        session_id = game_seq
        row_a = get_user(player_a) or {}
        row_b = get_user(player_b) or {}
        class_group = pick_game_class_group(row_a.get("class_group"), row_b.get("class_group"))
        session = {
            "id": session_id,
            "players": [int(player_a), int(player_b)],
            "ready": set(),
            "state": "ready",
            "score": {int(player_a): 0, int(player_b): 0},
            "class_group": class_group,
            "round": 0,
            "answer": None,
            "winner": None,
            "event": threading.Event(),
            "lock": threading.Lock(),
            "match_messages": {},
            "round_messages": [],
            "attempt_messages": [],
        }
        game_sessions[session_id] = session
        chat_to_game[int(player_a)] = session_id
        chat_to_game[int(player_b)] = session_id
    return session


def get_session_by_chat(chat_id):
    with receiver_game_lock:
        session_id = chat_to_game.get(int(chat_id))
        if session_id is None:
            return None
        return game_sessions.get(session_id)


def remove_game_session(session_id):
    with receiver_game_lock:
        session = game_sessions.pop(int(session_id), None)
        if not session:
            return
        for player in session["players"]:
            chat_to_game.pop(int(player), None)
            clear_pending_report_target(player)


def queue_add_player(chat_id):
    with receiver_queue_lock:
        chat_id = int(chat_id)
        if chat_id not in online_waiting_set:
            online_waiting_set.add(chat_id)
            online_waiting_queue.append(chat_id)


def queue_remove_player(chat_id):
    with receiver_queue_lock:
        chat_id = int(chat_id)
        if chat_id in online_waiting_set:
            online_waiting_set.remove(chat_id)
        online_waiting_queue[:] = [x for x in online_waiting_queue if int(x) != chat_id]


def queue_is_waiting(chat_id):
    with receiver_queue_lock:
        return int(chat_id) in online_waiting_set


def queue_pick_opponent(chat_id):
    with receiver_queue_lock:
        own = int(chat_id)
        while online_waiting_queue:
            candidate = int(online_waiting_queue.pop(0))
            online_waiting_set.discard(candidate)
            if candidate != own:
                return candidate
        return None


def set_game_invite(inviter_id, target_id):
    inviter = int(inviter_id)
    target = int(target_id)
    with friend_invite_lock:
        friend_game_invites[target] = {
            "from": inviter,
            "created_at": time.time(),
        }


def get_game_invite(target_id):
    target = int(target_id)
    with friend_invite_lock:
        invite = friend_game_invites.get(target)
        return dict(invite) if invite else None


def pop_game_invite(target_id, expected_from=None):
    target = int(target_id)
    with friend_invite_lock:
        invite = friend_game_invites.get(target)
        if not invite:
            return None
        if expected_from is not None and int(invite.get("from")) != int(expected_from):
            return None
        return friend_game_invites.pop(target, None)


def clear_game_invites_for(chat_id):
    user_id = int(chat_id)
    with friend_invite_lock:
        friend_game_invites.pop(user_id, None)
        stale_targets = [target for target, invite in friend_game_invites.items() if int(invite.get("from")) == user_id]
        for target in stale_targets:
            friend_game_invites.pop(target, None)


def notify_game_ready(session):
    first, second = session["players"]
    text = (
        "Соперник найден.\n"
        f"Уровень игры: {session['class_group']}\n"
        f"Раундов: {GAME_ROUNDS}\n"
        "Правила:\n"
        "- Кто первым отправит правильный ответ, получает 1 очко.\n"
        f"- На раунд {GAME_QUESTION_TIMEOUT} сек.\n"
        "Когда оба готовы, нажмите START."
    )
    first_msg = send_text(RECEIVER_BOT_TOKEN, first, text, reply_markup=receiver_game_ready_keyboard())
    second_msg = send_text(RECEIVER_BOT_TOKEN, second, text, reply_markup=receiver_game_ready_keyboard())
    session["match_messages"][first] = first_msg.get("message_id")
    session["match_messages"][second] = second_msg.get("message_id")


def send_game_message_to_players(session, text):
    for player in session["players"]:
        send_text(RECEIVER_BOT_TOKEN, player, text)


def get_game_opponent(session, player_id):
    player = int(player_id)
    players = session["players"]
    return players[0] if players[1] == player else players[1]


def cleanup_game_round_messages(session):
    with session["lock"]:
        round_messages = list(session.get("round_messages") or [])
        attempt_messages = list(session.get("attempt_messages") or [])
        session["round_messages"] = []
        session["attempt_messages"] = []
    for chat_id, message_id in round_messages + attempt_messages:
        if message_id:
            delete_message(RECEIVER_BOT_TOKEN, chat_id, message_id)


def send_game_round_prompt(session, current_round, question):
    sent = []
    for player in session["players"]:
        opponent_id = get_game_opponent(session, player)
        payload = (
            f"Раунд {current_round}/{GAME_ROUNDS}\n"
            f"{question}\n"
            "Ответ отправь сообщением."
        )
        result = send_text(
            RECEIVER_BOT_TOKEN,
            player,
            payload,
            reply_markup=receiver_game_round_keyboard(opponent_id),
        )
        message_id = result.get("message_id")
        if message_id:
            sent.append((int(player), int(message_id)))
    with session["lock"]:
        session["round_messages"] = sent


def run_game_session(session_id):
    session = get_session_by_chat(session_id)
    if session is None:
        return

    with session["lock"]:
        if session["state"] != "ready":
            return
        session["state"] = "countdown"
        session["round"] = 0
        session["score"] = {session["players"][0]: 0, session["players"][1]: 0}
        for player, message_id in session["match_messages"].items():
            if message_id:
                delete_message(RECEIVER_BOT_TOKEN, player, message_id)
        session["match_messages"] = {}

    for tick in [3, 2, 1]:
        send_game_message_to_players(session, f"Старт через {tick}...")
        time.sleep(GAME_COUNTDOWN_DELAY)

    with session["lock"]:
        session["state"] = "active"

    for current_round in range(1, GAME_ROUNDS + 1):
        cleanup_game_round_messages(session)
        question, answer = generate_game_question(session["class_group"])
        with session["lock"]:
            if session["state"] != "active":
                return
            session["round"] = current_round
            session["answer"] = answer
            session["winner"] = None
            session["event"].clear()

        send_game_round_prompt(session, current_round, question)

        session["event"].wait(timeout=GAME_QUESTION_TIMEOUT)

        with session["lock"]:
            winner = session["winner"]
            right_answer = session["answer"]
            session["answer"] = None
            session["winner"] = None

        if winner is not None:
            session["score"][winner] += 1
            winner_row = get_user(winner) or {"chat_id": winner}
            send_game_message_to_players(
                session,
                f"Раунд {current_round}: первым ответил {build_name(winner_row)}. +1 очко",
            )
        else:
            send_game_message_to_players(
                session,
                f"Раунд {current_round}: время вышло. Правильный ответ: {right_answer}",
            )

    cleanup_game_round_messages(session)
    p1, p2 = session["players"]
    score1 = int(session["score"].get(p1, 0))
    score2 = int(session["score"].get(p2, 0))

    if score1 > score2:
        update_user_game_stats(p1, wins=1, points=score1)
        update_user_game_stats(p2, losses=1, points=score2)
        result_title = "Победитель: игрок 1"
    elif score2 > score1:
        update_user_game_stats(p2, wins=1, points=score2)
        update_user_game_stats(p1, losses=1, points=score1)
        result_title = "Победитель: игрок 2"
    else:
        update_user_game_stats(p1, draws=1, points=score1)
        update_user_game_stats(p2, draws=1, points=score2)
        result_title = "Ничья"

    row1 = get_user(p1) or {"chat_id": p1}
    row2 = get_user(p2) or {"chat_id": p2}
    final_text = (
        "Игра завершена.\n"
        f"{result_title}\n"
        f"{build_name(row1)}: {score1}\n"
        f"{build_name(row2)}: {score2}"
    )
    for player in session["players"]:
        clear_pending_report_target(player)
        send_text(RECEIVER_BOT_TOKEN, player, final_text, reply_markup=receiver_main_keyboard())
        set_receiver_mode(player, "home")

    with session["lock"]:
        session["state"] = "finished"
    remove_game_session(session["id"])


def process_game_answer(chat_id, raw_text):
    session = get_session_by_chat(chat_id)
    if session is None:
        return False

    parsed = None
    is_correct = False
    with session["lock"]:
        if session["state"] != "active":
            return True
        expected = session.get("answer")
        if expected is None:
            return True
        if session.get("winner") is not None:
            return True
        parsed = parse_numeric_answer(raw_text)
        if parsed is None:
            return True
        is_correct = parsed == str(expected)
        if is_correct:
            session["winner"] = int(chat_id)
            session["event"].set()

    player_row = get_user(chat_id) or {"chat_id": chat_id}
    verdict = "верно ✅" if is_correct else "неверно ❌"
    log_text = f"{build_name(player_row)} ответ: {parsed} ({verdict})"
    sent = []
    for player in session["players"]:
        result = send_text(RECEIVER_BOT_TOKEN, player, log_text)
        msg_id = result.get("message_id")
        if msg_id:
            sent.append((int(player), int(msg_id)))
    if sent:
        with session["lock"]:
            session["attempt_messages"].extend(sent)
    return True


def leave_or_forfeit_game(chat_id):
    session = get_session_by_chat(chat_id)
    if session is None:
        return False

    player = int(chat_id)
    cleanup_game_round_messages(session)
    with session["lock"]:
        if session["state"] == "finished":
            return True
        session["state"] = "finished"
        players = list(session["players"])
        opponent = players[0] if players[1] == player else players[1]
        score_player = int(session["score"].get(player, 0))
        score_opponent = int(session["score"].get(opponent, 0))
        score_opponent += 1
        session["score"][opponent] = score_opponent
        session["score"][player] = score_player

    update_user_game_stats(opponent, wins=1, points=score_opponent)
    update_user_game_stats(player, losses=1, points=score_player)

    send_text(
        RECEIVER_BOT_TOKEN,
        opponent,
        "Соперник вышел из игры. Победа присуждена тебе.",
        reply_markup=receiver_main_keyboard(),
    )
    send_text(
        RECEIVER_BOT_TOKEN,
        player,
        "Ты вышел из онлайн-игры.",
        reply_markup=receiver_main_keyboard(),
    )
    clear_pending_report_target(opponent)
    clear_pending_report_target(player)
    set_receiver_mode(opponent, "home")
    set_receiver_mode(player, "home")
    remove_game_session(session["id"])
    return True


def cleanup_blocked_user(chat_id, error):
    if error.error_code in (400, 403):
        lowered = (error.description or "").lower()
        if "blocked" in lowered or "chat not found" in lowered or "forbidden" in lowered:
            set_broadcast_enabled(chat_id, False)


def send_to_targets(text, target_ids):
    delivered = 0
    failed = 0
    for chat_id in target_ids:
        try:
            send_text(RECEIVER_BOT_TOKEN, chat_id, text)
            delivered += 1
        except TelegramApiError as exc:
            failed += 1
            cleanup_blocked_user(chat_id, exc)
        except (urllib.error.URLError, TimeoutError, OSError):
            failed += 1
    return delivered, failed


def broadcast_text(text):
    targets = get_broadcast_targets()
    return send_to_targets(text, targets)


def relay_to_admin(user_chat_id, user_obj, text):
    admin_id = get_admin_id()
    if admin_id is None:
        return
    name = build_name(
        {
            "chat_id": user_chat_id,
            "username": user_obj.get("username"),
            "first_name": user_obj.get("first_name"),
            "last_name": user_obj.get("last_name"),
        }
    )
    payload = (
        "Запрос, который не удалось вычислить автоматически:\n"
        f"ID: {user_chat_id}\n"
        f"Имя: {name}\n"
        f"Текст: {text[:MAX_RELAY_LEN]}"
    )
    try:
        send_text(SENDER_BOT_TOKEN, admin_id, payload)
    except Exception:  # noqa: BLE001
        pass


def relay_registration_to_admin(user_chat_id, user_obj, registration_name):
    admin_id = get_admin_id()
    if admin_id is None:
        return
    username = user_obj.get("username")
    username_line = f"Telegram username: @{username}" if username else "Telegram username: -"
    payload = (
        "Новая регистрация пользователя:\n"
        f"ID: {user_chat_id}\n"
        f"Имя регистрации: {registration_name}\n"
        f"Когда: {format_local_timestamp(utc_now())}\n"
        f"Telegram first_name: {user_obj.get('first_name') or '-'}\n"
        f"Telegram last_name: {user_obj.get('last_name') or '-'}\n"
        f"{username_line}"
    )
    try:
        send_text(SENDER_BOT_TOKEN, admin_id, payload)
    except Exception:  # noqa: BLE001
        pass


def relay_user_activity_to_admin(user_chat_id, user_obj, text):
    admin_id = get_admin_id()
    if admin_id is None:
        return
    username = user_obj.get("username")
    first_name = user_obj.get("first_name") or "-"
    last_name = user_obj.get("last_name") or "-"
    username_line = f"Username: @{username}" if username else "Username: -"
    payload = (
        "Сообщение пользователя:\n"
        f"ID: {user_chat_id}\n"
        f"Имя: {first_name} {last_name}\n"
        f"{username_line}\n"
        + f"Текст: {text[:MAX_RELAY_LEN]}"
    )
    try:
        send_text(SENDER_BOT_TOKEN, admin_id, payload)
    except Exception:  # noqa: BLE001
        pass


def report_side_name(row, prefix):
    data = {
        "chat_id": row.get(f"{prefix}_id"),
        "username": row.get(f"{prefix}_username"),
        "first_name": row.get(f"{prefix}_first_name"),
        "last_name": row.get(f"{prefix}_last_name"),
        "registration_name": row.get(f"{prefix}_registration_name"),
    }
    return build_name(data)


def relay_report_to_admin(report_id):
    admin_id = get_admin_id()
    if admin_id is None:
        return
    row = get_player_report(report_id)
    if not row:
        return
    payload = (
        f"Новая жалоба #{int(row['id'])}\n"
        f"От: {report_side_name(row, 'reporter')} (id:{int(row['reporter_id'])})\n"
        f"На: {report_side_name(row, 'target')} (id:{int(row['target_id'])})\n"
        f"Когда: {format_local_timestamp(row.get('created_at'))}\n"
        f"Причина: {row.get('reason') or '-'}"
    )
    try:
        send_text(
            SENDER_BOT_TOKEN,
            admin_id,
            payload,
            reply_markup={
                "inline_keyboard": [[{"text": "Открыть жалобу", "callback_data": f"adm:report:{int(row['id'])}:0"}]]
            },
        )
    except Exception:  # noqa: BLE001
        pass


def handle_receiver_message(message):
    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return

    chat_id = chat.get("id")
    if chat_id is None:
        return

    user_obj = message.get("from", {})
    text = (message.get("text") or "").strip()
    touch_user(chat_id, user_obj, text)
    text_lower = text.lower()
    current_mode = get_receiver_mode(chat_id)

    if is_command(text, "/start"):
        clear_pending_report_target(chat_id)
        if is_user_registered(chat_id):
            record_user_visit(chat_id)
            set_receiver_mode(chat_id, "home")
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                receiver_home_text(),
                reply_markup=receiver_main_keyboard(),
            )
        else:
            queue_remove_player(chat_id)
            leave_or_forfeit_game(chat_id)
            clear_game_invites_for(chat_id)
            clear_pending_report_target(chat_id)
            begin_receiver_registration(chat_id)
            set_receiver_mode(chat_id, "register")
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                registration_prompt_text(),
                reply_markup=remove_reply_keyboard(),
            )
        return

    if is_command(text, "/help") or text_lower in {"help", "хелп", "помощь"}:
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            receiver_help_text(),
            reply_markup=receiver_main_keyboard() if is_user_registered(chat_id) else remove_reply_keyboard(),
        )
        return

    if is_command(text, "/privacy"):
        row = get_user(chat_id)
        if row is None:
            send_text(RECEIVER_BOT_TOKEN, chat_id, "Данные не найдены.")
            return
        send_text(RECEIVER_BOT_TOKEN, chat_id, user_detail(row))
        return

    if is_command(text, "/stop"):
        queue_remove_player(chat_id)
        leave_or_forfeit_game(chat_id)
        clear_game_invites_for(chat_id)
        clear_pending_report_target(chat_id)
        clear_receiver_registration(chat_id)
        clear_receiver_mode(chat_id)
        clear_user_social_graph(chat_id)
        set_user_consent(chat_id, False)
        set_user_registration_name(chat_id, "")
        set_user_class_group(chat_id, "5-8")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Регистрация сброшена. Для запуска заново: /start",
            reply_markup=remove_reply_keyboard(),
        )
        return

    if text.startswith("/"):
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Неизвестная команда. Напиши /help",
            reply_markup=receiver_main_keyboard() if is_user_registered(chat_id) else remove_reply_keyboard(),
        )
        return

    if is_receiver_registration_pending(chat_id) or current_mode == "await_name_change":
        registration_name, validation_error = validate_registration_name(text)
        if validation_error:
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                f"{validation_error} Введи снова.",
            )
            return
        if is_registration_name_taken(registration_name, exclude_chat_id=chat_id):
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Такое имя уже занято. Выбери другое.",
            )
            return

        set_user_consent(chat_id, True)
        set_user_registration_name(chat_id, registration_name)
        clear_receiver_registration(chat_id)
        set_receiver_mode(chat_id, "home")

        if current_mode == "await_name_change":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Имя обновлено.",
                reply_markup=receiver_main_keyboard(),
            )
        else:
            record_user_visit(chat_id)
            log_registration_event(chat_id, registration_name)
            relay_registration_to_admin(chat_id, user_obj, registration_name)
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Регистрация завершена.",
                reply_markup=receiver_main_keyboard(),
            )
            send_text(RECEIVER_BOT_TOKEN, chat_id, receiver_home_text())
        return

    if not is_user_registered(chat_id):
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Сначала нажми /start и введи имя для регистрации.",
            reply_markup=remove_reply_keyboard(),
        )
        return

    if is_user_banned(chat_id):
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Доступ ограничен администратором.",
        )
        return

    pending_report_target = get_pending_report_target(chat_id)
    if pending_report_target is not None:
        if text_lower in {"cancel", "отмена"} or text == BTN_HOME:
            clear_pending_report_target(chat_id)
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Отправка жалобы отменена.",
                reply_markup=receiver_main_keyboard(),
            )
            return
        reason = (text or "").strip()
        if not reason:
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Напиши причину жалобы одним сообщением или отправь «Отмена».",
                reply_markup=receiver_main_keyboard(),
            )
            return
        report_id = create_player_report(chat_id, pending_report_target, reason)
        clear_pending_report_target(chat_id)
        relay_report_to_admin(report_id)
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            f"Жалоба отправлена. Номер: #{report_id}",
            reply_markup=receiver_main_keyboard(),
        )
        return

    if queue_is_waiting(chat_id):
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Поиск соперника уже запущен. Жди или нажми «Отменить поиск».",
        )
        return

    if process_game_answer(chat_id, text):
        return

    if current_mode == "await_friend_search":
        if text == BTN_HOME:
            set_receiver_mode(chat_id, "home")
            send_text(RECEIVER_BOT_TOKEN, chat_id, receiver_home_text(), reply_markup=receiver_main_keyboard())
            return
        if text == BTN_FRIENDS or text_lower in {"отмена", "cancel"}:
            set_receiver_mode(chat_id, "friends_menu")
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                receiver_friends_text(chat_id),
                reply_markup=receiver_friends_keyboard(),
            )
            return
        if not text:
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Введи @username или имя регистрации пользователя.",
                reply_markup=receiver_main_keyboard(),
            )
            return

        target_row = find_friend_target(text, chat_id)
        if not target_row:
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Пользователь не найден. Проверь @username или имя регистрации.",
                reply_markup=receiver_main_keyboard(),
            )
            return

        target_id = int(target_row["chat_id"])
        result = create_or_refresh_friend_request(chat_id, target_id)
        target_name = build_name(target_row)
        set_receiver_mode(chat_id, "friends_menu")

        if result == "self":
            send_text(RECEIVER_BOT_TOKEN, chat_id, "Себя добавить нельзя.", reply_markup=receiver_main_keyboard())
            return
        if result == "already_friends":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                f"Вы уже друзья с {target_name}.",
                reply_markup=receiver_main_keyboard(),
            )
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                receiver_friends_text(chat_id),
                reply_markup=receiver_friends_keyboard(),
            )
            return
        if result == "already_pending":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                f"Заявка для {target_name} уже отправлена.",
                reply_markup=receiver_main_keyboard(),
            )
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                receiver_friends_text(chat_id),
                reply_markup=receiver_friends_keyboard(),
            )
            return
        if result == "disabled":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Этот пользователь отключил прием заявок в друзья.",
                reply_markup=receiver_main_keyboard(),
            )
            return
        if result == "banned":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Нельзя отправить заявку этому пользователю.",
                reply_markup=receiver_main_keyboard(),
            )
            return
        if result in {"not_registered", "not_found"}:
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Пользователь пока недоступен для добавления в друзья.",
                reply_markup=receiver_main_keyboard(),
            )
            return
        if result == "auto_accepted":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                f"У вас взаимные заявки. Вы теперь друзья: {target_name}",
                reply_markup=receiver_main_keyboard(),
            )
            try:
                sender_row = get_user(chat_id) or {"chat_id": chat_id}
                send_text(
                    RECEIVER_BOT_TOKEN,
                    target_id,
                    f"У вас взаимные заявки. Вы теперь друзья: {build_name(sender_row)}",
                    reply_markup=receiver_main_keyboard(),
                )
            except Exception:  # noqa: BLE001
                pass
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                receiver_friends_text(chat_id),
                reply_markup=receiver_friends_keyboard(),
            )
            return
        if result != "created":
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                "Не удалось отправить заявку.",
                reply_markup=receiver_main_keyboard(),
            )
            return

        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            f"Заявка отправлена пользователю {target_name}.",
            reply_markup=receiver_main_keyboard(),
        )
        try:
            requester_row = get_user(chat_id) or {"chat_id": chat_id}
            send_text(
                RECEIVER_BOT_TOKEN,
                target_id,
                f"Новая заявка в друзья от {build_name(requester_row)}",
                reply_markup=receiver_friend_request_action_keyboard(chat_id),
            )
        except Exception:  # noqa: BLE001
            pass
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            receiver_friends_text(chat_id),
            reply_markup=receiver_friends_keyboard(),
        )
        return

    if text == BTN_HOME:
        set_receiver_mode(chat_id, "home")
        send_text(RECEIVER_BOT_TOKEN, chat_id, receiver_home_text(), reply_markup=receiver_main_keyboard())
        return

    if text == BTN_HELP:
        send_text(RECEIVER_BOT_TOKEN, chat_id, receiver_help_text(), reply_markup=receiver_main_keyboard())
        return

    if text == BTN_STATS:
        row = get_user(chat_id) or {}
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            receiver_personal_stats_text(row),
            reply_markup=receiver_main_keyboard(),
        )
        return

    if text == BTN_SETTINGS:
        set_receiver_mode(chat_id, "home")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Настройки профиля:",
            reply_markup=receiver_settings_keyboard(chat_id),
        )
        return

    if text == BTN_FRIENDS:
        set_receiver_mode(chat_id, "friends_menu")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            receiver_friends_text(chat_id),
            reply_markup=receiver_friends_keyboard(),
        )
        return

    if text == BTN_ONLINE:
        set_receiver_mode(chat_id, "online_menu")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            receiver_online_rules_text(),
            reply_markup=receiver_online_keyboard(),
        )
        return

    if text == BTN_CALC:
        set_receiver_mode(chat_id, "calc")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Режим калькулятора включен. Введи выражение.",
            reply_markup=receiver_main_keyboard(),
        )
        return

    if get_receiver_mode(chat_id) != "calc":
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Выбери действие кнопками. Для вычислений нажми «🧮 Начать считать».",
            reply_markup=receiver_main_keyboard(),
        )
        return

    if not text:
        send_text(RECEIVER_BOT_TOKEN, chat_id, "Отправь текст задачи, например: (2+3)*5")
        return

    relay_user_activity_to_admin(chat_id, user_obj, text)

    try:
        result = solve_math_text(text)
        increment_user_counters(
            chat_id,
            total=1,
            calc_success=1,
            last_calc_input=text[:MAX_RELAY_LEN],
            last_calc_output=result[:MAX_RELAY_LEN],
        )
        send_text(RECEIVER_BOT_TOKEN, chat_id, f"Ответ:\n{result}")
    except CalcEvalError:
        increment_user_counters(
            chat_id,
            total=1,
            calc_failed=1,
            relayed=1,
            last_calc_input=text[:MAX_RELAY_LEN],
        )
        relay_to_admin(chat_id, user_obj, text)
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Не понял выражение. Напиши help, чтобы увидеть форматы и примеры.",
        )


def handle_receiver_callback(callback_query):
    callback_id = callback_query.get("id")
    data = (callback_query.get("data") or "").strip()
    from_user = callback_query.get("from", {})
    message = callback_query.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    message_id = message.get("message_id")

    if callback_id is None:
        return
    if chat_id is None or message_id is None:
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Не удалось обработать.", show_alert=True)
        return

    touch_user(chat_id, from_user)

    if not data.startswith("rcv:"):
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Неизвестное действие.")
        return

    if data == "rcv:home":
        queue_remove_player(chat_id)
        clear_game_invites_for(chat_id)
        clear_pending_report_target(chat_id)
        if not is_user_registered(chat_id):
            begin_receiver_registration(chat_id)
            set_receiver_mode(chat_id, "register")
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Сначала регистрация.", show_alert=True)
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                registration_prompt_text(),
                reply_markup=remove_reply_keyboard(),
            )
            return
        if get_session_by_chat(chat_id):
            leave_or_forfeit_game(chat_id)
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Выход из игры.")
            return
        set_receiver_mode(chat_id, "home")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Главное меню.")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            receiver_home_text(),
            reply_markup=receiver_main_keyboard(),
        )
        return

    if not is_user_registered(chat_id):
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Сначала /start и регистрация.", show_alert=True)
        return

    if is_user_banned(chat_id):
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Доступ ограничен.", show_alert=True)
        return

    if data.startswith("rcv:report:"):
        try:
            target_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректная жалоба.", show_alert=True)
            return
        session = get_session_by_chat(chat_id)
        if session is None:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Пожаловаться можно во время игры.", show_alert=True)
            return
        opponent_id = get_game_opponent(session, chat_id)
        if int(target_id) != int(opponent_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Можно пожаловаться только на текущего соперника.", show_alert=True)
            return
        set_pending_report_target(chat_id, target_id)
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Опиши жалобу.")
        send_text(
            RECEIVER_BOT_TOKEN,
            chat_id,
            "Напиши причину жалобы одним сообщением. Для отмены напиши «Отмена».",
            reply_markup=receiver_main_keyboard(),
        )
        return

    if data == "rcv:set_name":
        begin_receiver_registration(chat_id)
        set_receiver_mode(chat_id, "await_name_change")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Введи новое имя.")
        send_text(RECEIVER_BOT_TOKEN, chat_id, "Введи новое имя регистрации.")
        return

    if data == "rcv:set_class_menu":
        answer_callback(RECEIVER_BOT_TOKEN, callback_id)
        receiver_edit_or_send(chat_id, message_id, "Выбери класс/уровень:", reply_markup=receiver_class_keyboard())
        return

    if data == "rcv:toggle_friend_requests":
        row = get_user(chat_id) or {}
        current = int(row.get("allow_friend_requests") or 0) == 1
        set_user_allow_friend_requests(chat_id, not current)
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Настройка обновлена.")
        receiver_edit_or_send(
            chat_id,
            message_id,
            "Настройки профиля:",
            reply_markup=receiver_settings_keyboard(chat_id),
        )
        return

    if data == "rcv:toggle_searchable":
        row = get_user(chat_id) or {}
        current = int(row.get("searchable_by_name") or 0) == 1
        set_user_searchable_by_name(chat_id, not current)
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Настройка обновлена.")
        receiver_edit_or_send(
            chat_id,
            message_id,
            "Настройки профиля:",
            reply_markup=receiver_settings_keyboard(chat_id),
        )
        return

    if data == "rcv:friends_menu":
        set_receiver_mode(chat_id, "friends_menu")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Раздел друзей.")
        receiver_edit_or_send(
            chat_id,
            message_id,
            receiver_friends_text(chat_id),
            reply_markup=receiver_friends_keyboard(),
        )
        return

    if data == "rcv:friend_add":
        set_receiver_mode(chat_id, "await_friend_search")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Введи ник или имя.")
        receiver_edit_or_send(
            chat_id,
            message_id,
            "Введи @username или имя регистрации пользователя для отправки заявки в друзья.",
            reply_markup={"inline_keyboard": [[{"text": "⬅ Назад", "callback_data": "rcv:friends_menu"}]]},
        )
        return

    if data == "rcv:friend_incoming":
        answer_callback(RECEIVER_BOT_TOKEN, callback_id)
        text_value, keyboard = receiver_incoming_requests_view(chat_id)
        receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
        return

    if data.startswith("rcv:fr_accept:") or data.startswith("rcv:fr_reject:"):
        parts = data.split(":")
        try:
            requester_id = int(parts[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректная заявка.", show_alert=True)
            return

        accept = parts[1] == "fr_accept"
        if not respond_friend_request(chat_id, requester_id, accept=accept):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Заявка уже недоступна.", show_alert=True)
            text_value, keyboard = receiver_incoming_requests_view(chat_id)
            receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
            return

        requester_row = get_user(requester_id) or {"chat_id": requester_id}
        actor_row = get_user(chat_id) or {"chat_id": chat_id}
        if accept:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Заявка принята.")
            try:
                send_text(
                    RECEIVER_BOT_TOKEN,
                    requester_id,
                    f"{build_name(actor_row)} принял(а) твою заявку в друзья.",
                    reply_markup=receiver_main_keyboard(),
                )
            except Exception:  # noqa: BLE001
                pass
            send_text(
                RECEIVER_BOT_TOKEN,
                chat_id,
                f"Теперь вы друзья: {build_name(requester_row)}",
                reply_markup=receiver_main_keyboard(),
            )
        else:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Заявка отклонена.")
            try:
                send_text(
                    RECEIVER_BOT_TOKEN,
                    requester_id,
                    f"{build_name(actor_row)} отклонил(а) твою заявку в друзья.",
                    reply_markup=receiver_main_keyboard(),
                )
            except Exception:  # noqa: BLE001
                pass
        text_value, keyboard = receiver_incoming_requests_view(chat_id)
        receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
        return

    if data == "rcv:friend_list":
        answer_callback(RECEIVER_BOT_TOKEN, callback_id)
        text_value, keyboard = receiver_friend_list_view(chat_id)
        receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
        return

    if data.startswith("rcv:friend_view:"):
        try:
            friend_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректный пользователь.", show_alert=True)
            return
        if not are_friends(chat_id, friend_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Пользователь не в друзьях.", show_alert=True)
            text_value, keyboard = receiver_friend_list_view(chat_id)
            receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
            return
        friend_row = get_user(friend_id)
        if not friend_row:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Пользователь не найден.", show_alert=True)
            text_value, keyboard = receiver_friend_list_view(chat_id)
            receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
            return
        answer_callback(RECEIVER_BOT_TOKEN, callback_id)
        text_value = "\n".join(
            [
                f"Друг: {build_name(friend_row)}",
                f"ID: {friend_id}",
                f"Имя регистрации: {friend_row.get('registration_name') or '-'}",
                f"Класс/уровень: {friend_row.get('class_group') or '5-8'}",
                f"Последний онлайн: {friend_row.get('last_seen_at') or '-'}",
            ]
        )
        receiver_edit_or_send(
            chat_id,
            message_id,
            text_value,
            reply_markup=receiver_friend_actions_keyboard(friend_id),
        )
        return

    if data.startswith("rcv:friend_remove:"):
        try:
            friend_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректный пользователь.", show_alert=True)
            return
        removed = remove_friendship(chat_id, friend_id)
        pop_game_invite(chat_id, expected_from=friend_id)
        pop_game_invite(friend_id, expected_from=chat_id)
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Удалено из друзей." if removed else "Связь уже удалена.")
        text_value, keyboard = receiver_friend_list_view(chat_id)
        receiver_edit_or_send(chat_id, message_id, text_value, reply_markup=keyboard)
        return

    if data.startswith("rcv:friend_invite:"):
        try:
            friend_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректный пользователь.", show_alert=True)
            return
        if not are_friends(chat_id, friend_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Можно приглашать только друзей.", show_alert=True)
            return
        if get_session_by_chat(chat_id) or get_session_by_chat(friend_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Кто-то уже в игре.", show_alert=True)
            return
        if queue_is_waiting(chat_id) or queue_is_waiting(friend_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Кто-то уже ищет соперника.", show_alert=True)
            return

        set_game_invite(chat_id, friend_id)
        inviter_row = get_user(chat_id) or {"chat_id": chat_id}
        try:
            send_text(
                RECEIVER_BOT_TOKEN,
                friend_id,
                (
                    f"{build_name(inviter_row)} приглашает тебя в онлайн-дуэль по математике.\n"
                    "Принять приглашение?"
                ),
                reply_markup=receiver_invite_keyboard(chat_id),
            )
        except Exception:  # noqa: BLE001
            pop_game_invite(friend_id, expected_from=chat_id)
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Не удалось отправить приглашение.", show_alert=True)
            return
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Приглашение отправлено.")
        receiver_edit_or_send(
            chat_id,
            message_id,
            "Приглашение отправлено. Ждем ответ друга.",
            reply_markup=receiver_friend_actions_keyboard(friend_id),
        )
        return

    if data.startswith("rcv:invite_accept:"):
        try:
            inviter_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректное приглашение.", show_alert=True)
            return

        invite = pop_game_invite(chat_id, expected_from=inviter_id)
        if not invite:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Приглашение не найдено или устарело.", show_alert=True)
            return
        if (time.time() - float(invite.get("created_at") or 0.0)) > 180:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Приглашение устарело.", show_alert=True)
            return
        if not are_friends(chat_id, inviter_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Пользователь не в друзьях.", show_alert=True)
            return
        if get_session_by_chat(chat_id) or get_session_by_chat(inviter_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Кто-то уже в игре.", show_alert=True)
            return
        if queue_is_waiting(chat_id) or queue_is_waiting(inviter_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Кто-то уже в поиске соперника.", show_alert=True)
            return

        queue_remove_player(chat_id)
        queue_remove_player(inviter_id)
        clear_game_invites_for(chat_id)
        clear_game_invites_for(inviter_id)
        session = get_or_create_game_session(inviter_id, chat_id)
        set_receiver_mode(chat_id, "game_ready")
        set_receiver_mode(inviter_id, "game_ready")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Приглашение принято.")
        notify_game_ready(session)
        return

    if data.startswith("rcv:invite_decline:"):
        try:
            inviter_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Некорректное приглашение.", show_alert=True)
            return
        invite = pop_game_invite(chat_id, expected_from=inviter_id)
        if not invite:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Приглашение уже недоступно.", show_alert=True)
            return
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Приглашение отклонено.")
        try:
            actor_row = get_user(chat_id) or {"chat_id": chat_id}
            send_text(
                RECEIVER_BOT_TOKEN,
                inviter_id,
                f"{build_name(actor_row)} отклонил(а) приглашение в дуэль.",
                reply_markup=receiver_main_keyboard(),
            )
        except Exception:  # noqa: BLE001
            pass
        receiver_edit_or_send(
            chat_id,
            message_id,
            receiver_friends_text(chat_id),
            reply_markup=receiver_friends_keyboard(),
        )
        return

    if data.startswith("rcv:set_class:"):
        class_group = data.split(":", 2)[2].strip()
        if class_group not in {"1-4", "5-8", "9-11", "pro"}:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Неизвестный уровень.")
            return
        set_user_class_group(chat_id, class_group)
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Уровень сохранен.")
        receiver_edit_or_send(
            chat_id,
            message_id,
            f"Класс/уровень обновлен: {class_group}",
            reply_markup=receiver_settings_keyboard(chat_id),
        )
        return

    if data == "rcv:online_rules":
        answer_callback(RECEIVER_BOT_TOKEN, callback_id)
        receiver_edit_or_send(chat_id, message_id, receiver_online_rules_text(), reply_markup=receiver_online_keyboard())
        return

    if data == "rcv:online_find":
        if get_session_by_chat(chat_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Ты уже в онлайн-игре.", show_alert=True)
            return
        if queue_is_waiting(chat_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Поиск уже запущен.", show_alert=True)
            return
        clear_game_invites_for(chat_id)
        opponent_id = queue_pick_opponent(chat_id)
        if opponent_id is None:
            queue_add_player(chat_id)
            set_receiver_mode(chat_id, "online_wait")
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Поиск запущен.")
            receiver_edit_or_send(
                chat_id,
                message_id,
                "Ищем соперника. Когда найдется, бот сообщит.",
                reply_markup=receiver_waiting_keyboard(),
            )
            return

        clear_game_invites_for(chat_id)
        clear_game_invites_for(opponent_id)
        session = get_or_create_game_session(opponent_id, chat_id)
        set_receiver_mode(chat_id, "game_ready")
        set_receiver_mode(opponent_id, "game_ready")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Соперник найден.")
        notify_game_ready(session)
        return

    if data == "rcv:online_cancel":
        queue_remove_player(chat_id)
        set_receiver_mode(chat_id, "online_menu")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Поиск отменен.")
        receiver_edit_or_send(chat_id, message_id, receiver_online_rules_text(), reply_markup=receiver_online_keyboard())
        return

    if data == "rcv:online_leave":
        queue_remove_player(chat_id)
        clear_game_invites_for(chat_id)
        clear_pending_report_target(chat_id)
        if leave_or_forfeit_game(chat_id):
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Игра завершена.")
            return
        set_receiver_mode(chat_id, "home")
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Выход.")
        send_text(RECEIVER_BOT_TOKEN, chat_id, receiver_home_text(), reply_markup=receiver_main_keyboard())
        return

    if data == "rcv:game_start":
        session = get_session_by_chat(chat_id)
        if session is None:
            answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Сессия не найдена.", show_alert=True)
            return
        should_start = False
        with session["lock"]:
            if session["state"] != "ready":
                answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Игра уже запущена.")
                return
            session["ready"].add(int(chat_id))
            ready_count = len(session["ready"])
            total = len(session["players"])
            if ready_count >= total:
                should_start = True
        answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Готово.")
        if should_start:
            send_game_message_to_players(session, "Оба игрока готовы. Подготовка...")
            threading.Thread(target=run_game_session, args=(session["id"],), daemon=True).start()
        else:
            send_text(RECEIVER_BOT_TOKEN, chat_id, "Ожидаем второго игрока...")
        return

    answer_callback(RECEIVER_BOT_TOKEN, callback_id, "Неизвестная кнопка.")


def handle_receiver_update(update):
    callback_query = update.get("callback_query")
    if callback_query:
        handle_receiver_callback(callback_query)
        return
    message = update.get("message")
    if message:
        handle_receiver_message(message)


def is_admin_user(user_id):
    admin_id = get_admin_id()
    return admin_id is not None and int(admin_id) == int(user_id)


def admin_password_prompt(stage):
    if stage == 1:
        return "Введите пароль (1/3):"
    if stage == 2:
        return "Повтори пароль (2/3):"
    if stage == 3:
        return "Повтори пароль еще раз (3/3):"
    return "Введите пароль:"


def handle_admin_password_input(chat_id, user_id, text):
    stage = get_admin_auth_stage(user_id)
    if stage is None:
        return False

    if text.strip() != ADMIN_PASSWORD:
        clear_admin_auth(user_id)
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Неверный пароль. Доступ запрещен.\nНажми /start и попробуй снова.",
        )
        return True

    if stage < 3:
        next_stage = stage + 1
        set_admin_auth_stage(user_id, next_stage)
        send_text(SENDER_BOT_TOKEN, chat_id, admin_password_prompt(next_stage))
        return True

    set_admin_id(user_id)
    set_admin_authenticated(user_id, True)
    set_admin_mode(None, None, [])
    send_text(SENDER_BOT_TOKEN, chat_id, "Пароль принят. Доступ открыт.")
    show_panel(chat_id)
    return True


def is_admin_session_allowed(user_id):
    return is_admin_user(user_id) and is_admin_authenticated(user_id)


def show_panel(chat_id):
    send_text(SENDER_BOT_TOKEN, chat_id, admin_panel_text(), reply_markup=admin_main_keyboard())


def sender_edit_or_send(chat_id, message_id, text, reply_markup=None):
    try:
        edit_text(SENDER_BOT_TOKEN, chat_id, message_id, text, reply_markup=reply_markup)
    except TelegramApiError:
        send_text(SENDER_BOT_TOKEN, chat_id, text, reply_markup=reply_markup)


def show_user_detail(chat_id, message_id, target_id, offset):
    row = get_user(target_id)
    if row is None:
        sender_edit_or_send(
            chat_id,
            message_id,
            "Пользователь не найден.",
            reply_markup={"inline_keyboard": [[{"text": "К списку", "callback_data": f"adm:users:{offset}"}]]},
        )
        return
    sender_edit_or_send(
        chat_id,
        message_id,
        user_detail(row),
        reply_markup=build_user_keyboard(row, offset),
    )


def show_user_stats(chat_id, message_id, target_id, offset):
    row = get_user(target_id)
    if row is None:
        sender_edit_or_send(
            chat_id,
            message_id,
            "Пользователь не найден.",
            reply_markup={"inline_keyboard": [[{"text": "К списку", "callback_data": f"adm:users:{offset}"}]]},
        )
        return
    sender_edit_or_send(
        chat_id,
        message_id,
        user_stats_text(row),
        reply_markup=build_user_keyboard(row, offset),
    )


def top_users_text(limit=10):
    rows = get_top_users(limit=limit)
    lines = ["Топ активных пользователей:"]
    if not rows:
        lines.append("Список пуст.")
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"{idx}. {build_name(row)} | id:{row.get('chat_id')} | points:{int(row.get('game_points') or 0)} | "
            f"W/L/D:{int(row.get('game_wins') or 0)}/{int(row.get('game_losses') or 0)}/{int(row.get('game_draws') or 0)} | "
            f"msgs:{int(row.get('total_messages') or 0)} | visits:{int(row.get('visit_count') or 0)} | "
            f"ok:{int(row.get('calc_success_count') or 0)} | err:{int(row.get('calc_failed_count') or 0)} | "
            f"relayed:{int(row.get('relayed_count') or 0)} | banned:{int(row.get('is_banned') or 0)}"
        )
    return "\n".join(lines)


def handle_sender_callback(callback_query):
    callback_id = callback_query.get("id")
    data = callback_query.get("data") or ""
    message = callback_query.get("message", {})
    from_user = callback_query.get("from", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    user_id = from_user.get("id")

    if callback_id is None:
        return
    if chat_id is None or message_id is None or user_id is None:
        answer_callback(SENDER_BOT_TOKEN, callback_id, "Не удалось обработать.", show_alert=True)
        return

    if not is_admin_session_allowed(user_id):
        answer_callback(SENDER_BOT_TOKEN, callback_id, "Сначала /start и пароль.", show_alert=True)
        return

    answer_callback(SENDER_BOT_TOKEN, callback_id)

    if data == "adm:panel" or data == "adm:stats":
        sender_edit_or_send(chat_id, message_id, admin_panel_text(), reply_markup=admin_main_keyboard())
        return

    if data == "adm:autoclean_menu":
        sender_edit_or_send(chat_id, message_id, admin_autoclean_text(), reply_markup=admin_autoclean_keyboard())
        return

    if data.startswith("adm:autoclean_set:"):
        try:
            seconds = int(data.split(":")[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректное значение автоочистки.")
            return
        if seconds < 0:
            seconds = 0
        if seconds > 7 * 86400:
            seconds = 7 * 86400
        set_admin_autoclean_seconds(seconds)
        sender_edit_or_send(chat_id, message_id, admin_autoclean_text(), reply_markup=admin_autoclean_keyboard())
        return

    if data.startswith("adm:reports:"):
        try:
            offset = int(data.split(":")[2])
        except (IndexError, ValueError):
            offset = 0
        text, keyboard = build_reports_page(offset)
        sender_edit_or_send(chat_id, message_id, text, reply_markup=keyboard)
        return

    if data.startswith("adm:reportclose:"):
        parts = data.split(":")
        try:
            report_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректная жалоба.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        close_player_report(report_id)
        row = get_player_report(report_id)
        keyboard = {
            "inline_keyboard": [
                [{"text": "К жалобам", "callback_data": f"adm:reports:{offset}"}],
                [{"text": "Меню", "callback_data": "adm:panel"}],
            ]
        }
        sender_edit_or_send(chat_id, message_id, report_detail_text(row), reply_markup=keyboard)
        return

    if data.startswith("adm:report:"):
        parts = data.split(":")
        try:
            report_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректная жалоба.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        row = get_player_report(report_id)
        if not row:
            sender_edit_or_send(
                chat_id,
                message_id,
                "Жалоба не найдена.",
                reply_markup={"inline_keyboard": [[{"text": "К жалобам", "callback_data": f"adm:reports:{offset}"}]]},
            )
            return
        buttons = []
        if (row.get("status") or "open") == "open":
            buttons.append([{"text": "Закрыть жалобу", "callback_data": f"adm:reportclose:{report_id}:{offset}"}])
        buttons.append([{"text": "К жалобам", "callback_data": f"adm:reports:{offset}"}])
        buttons.append([{"text": "Меню", "callback_data": "adm:panel"}])
        sender_edit_or_send(chat_id, message_id, report_detail_text(row), reply_markup={"inline_keyboard": buttons})
        return

    if data.startswith("adm:registrations:"):
        try:
            offset = int(data.split(":")[2])
        except (IndexError, ValueError):
            offset = 0
        text, keyboard = build_registrations_page(offset)
        sender_edit_or_send(chat_id, message_id, text, reply_markup=keyboard)
        return

    if data == "adm:top":
        sender_edit_or_send(
            chat_id,
            message_id,
            top_users_text(),
            reply_markup={"inline_keyboard": [[{"text": "Меню", "callback_data": "adm:panel"}]]},
        )
        return

    if data == "adm:broadcast_all":
        set_admin_mode("broadcast_all")
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Режим: рассылка всем.\nОтправь текст или ссылку одним сообщением.",
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data == "adm:pick_targets":
        set_admin_mode("pick_targets")
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Режим: выборочная рассылка.\nПришли id/@username через запятую.",
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data == "adm:pick_direct":
        set_admin_mode("pick_direct")
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Режим: отправка одному.\nПришли ID или @username.",
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data == "adm:find_user":
        set_admin_mode("find_user")
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Режим: поиск пользователя.\nПришли ID или @username.",
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data == "adm:cancel_mode":
        set_admin_mode(None, None, [])
        show_panel(chat_id)
        return

    if data.startswith("adm:users:"):
        try:
            offset = int(data.split(":")[2])
        except (IndexError, ValueError):
            offset = 0
        text, keyboard = build_users_page(offset)
        sender_edit_or_send(chat_id, message_id, text, reply_markup=keyboard)
        return

    if data.startswith("adm:user:"):
        parts = data.split(":")
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        show_user_detail(chat_id, message_id, target_id, offset)
        return

    if data.startswith("adm:userdata:"):
        parts = data.split(":")
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        show_user_detail(chat_id, message_id, target_id, offset)
        return

    if data.startswith("adm:userstats:"):
        parts = data.split(":")
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        show_user_stats(chat_id, message_id, target_id, offset)
        return

    if data.startswith("adm:userregs:"):
        parts = data.split(":")
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        row = get_user(target_id)
        if row is None:
            sender_edit_or_send(
                chat_id,
                message_id,
                "Пользователь не найден.",
                reply_markup={"inline_keyboard": [[{"text": "К списку", "callback_data": f"adm:users:{offset}"}]]},
            )
            return
        sender_edit_or_send(
            chat_id,
            message_id,
            user_registration_events_text(row),
            reply_markup=build_user_keyboard(row, offset),
        )
        return

    if data.startswith("adm:compose:"):
        try:
            target_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        set_admin_mode("compose_direct", target_id=target_id, target_ids=[])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Режим: сообщение пользователю {target_id}.\nОтправь текст.",
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data.startswith("adm:rename:"):
        try:
            target_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        set_admin_mode("rename_user", target_id=target_id, target_ids=[])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Режим: смена имени пользователю {target_id}.\nПришли новое имя регистрации.",
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data.startswith("adm:addfriend:"):
        try:
            target_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        set_admin_mode("add_friend_for_user", target_id=target_id, target_ids=[])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            (
                f"Режим: добавить друга пользователю {target_id}.\n"
                "Пришли ID/@username второго пользователя."
            ),
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data.startswith("adm:banfor:"):
        try:
            target_id = int(data.split(":")[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        set_admin_mode("ban_for_user", target_id=target_id, target_ids=[])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            (
                f"Режим: временный бан для {target_id}.\n"
                "Пришли срок, например: 1h, 12h, 1d, 12:00, 2026-02-20 18:30"
            ),
            reply_markup=admin_cancel_keyboard(),
        )
        return

    if data.startswith("adm:mute:") or data.startswith("adm:unmute:"):
        parts = data.split(":")
        action = parts[1]
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        set_broadcast_enabled(target_id, action == "unmute")
        show_user_detail(chat_id, message_id, target_id, offset)
        return

    if data.startswith("adm:ban:") or data.startswith("adm:unban:"):
        parts = data.split(":")
        action = parts[1]
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        is_ban = action == "ban"
        set_user_banned(target_id, is_ban, reason="manual_admin_action" if is_ban else None)
        if is_ban:
            reset_runtime_state_for_user(target_id)
            try_notify_ban(target_id)
        show_user_detail(chat_id, message_id, target_id, offset)
        return

    if data.startswith("adm:remove:"):
        parts = data.split(":")
        try:
            target_id = int(parts[2])
        except (IndexError, ValueError):
            send_text(SENDER_BOT_TOKEN, chat_id, "Некорректный пользователь.")
            return
        try:
            offset = int(parts[3])
        except (IndexError, ValueError):
            offset = 0
        reset_runtime_state_for_user(target_id)
        notify_removed_account(target_id)
        remove_user(target_id)
        text, keyboard = build_users_page(offset)
        sender_edit_or_send(chat_id, message_id, f"Пользователь {target_id} удален.\n\n{text}", reply_markup=keyboard)
        return

    send_text(SENDER_BOT_TOKEN, chat_id, "Неизвестное действие. /panel")


def perform_direct_send(chat_id, target_id, message_text):
    delivered, failed = send_to_targets(message_text, [target_id])
    send_text(
        SENDER_BOT_TOKEN,
        chat_id,
        f"Отправка одному пользователю завершена.\nДоставлено: {delivered}\nОшибок: {failed}",
    )


def perform_broadcast(chat_id, message_text):
    delivered, failed = broadcast_text(message_text)
    send_text(
        SENDER_BOT_TOKEN,
        chat_id,
        f"Сообщение успешно отправлено.\nДоставлено: {delivered}\nОшибок: {failed}",
    )


def handle_sender_mode(chat_id, text):
    state = get_admin_mode()
    mode = state.get("type")
    if not mode:
        return False

    if mode == "broadcast_all":
        perform_broadcast(chat_id, text)
        set_admin_mode(None, None, [])
        show_panel(chat_id)
        return True

    if mode == "pick_targets":
        targets, unresolved = parse_target_identifiers_csv(text)
        if not targets:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Не удалось найти получателей. Формат: id/@username,id/@username",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        unresolved_text = ", ".join(unresolved) if unresolved else "-"
        set_admin_mode("compose_targets", target_id=None, target_ids=targets)
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            (
                f"Получатели выбраны: {len(targets)}\n"
                f"Не найдены: {unresolved_text}\n"
                "Теперь пришли текст или ссылку для рассылки."
            ),
            reply_markup=admin_cancel_keyboard(),
        )
        return True

    if mode == "compose_targets":
        targets = state.get("target_ids") or []
        if not targets:
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        delivered, failed = send_to_targets(text, targets)
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            (
                "Выборочная рассылка завершена.\n"
                f"Целей: {len(targets)}\n"
                f"Доставлено: {delivered}\n"
                f"Ошибок: {failed}"
            ),
        )
        set_admin_mode(None, None, [])
        show_panel(chat_id)
        return True

    if mode == "pick_direct":
        user_row = resolve_user_identifier(text)
        if not user_row:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Пользователь не найден. Пришли корректный ID или @username.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        target_id = int(user_row["chat_id"])
        set_admin_mode("compose_direct", target_id=target_id, target_ids=[])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Выбран пользователь {target_id} ({build_name(user_row)}).\nТеперь пришли текст сообщения.",
            reply_markup=admin_cancel_keyboard(),
        )
        return True

    if mode == "compose_direct":
        target_id = parse_chat_id(state.get("target_id"))
        if target_id is None:
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        perform_direct_send(chat_id, target_id, text)
        set_admin_mode(None, None, [])
        show_panel(chat_id)
        return True

    if mode == "find_user":
        user_row = resolve_user_identifier(text)
        if not user_row:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Пользователь не найден. Пришли ID или @username.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            user_detail(user_row),
            reply_markup=build_user_keyboard(user_row, 0),
        )
        set_admin_mode(None, None, [])
        return True

    if mode == "rename_user":
        target_id = parse_chat_id(state.get("target_id"))
        if target_id is None:
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        if not get_user(target_id):
            send_text(SENDER_BOT_TOKEN, chat_id, "Пользователь не найден.")
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        registration_name, validation_error = validate_registration_name(text)
        if validation_error:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                f"{validation_error} Пришли новое имя еще раз.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        if is_registration_name_taken(registration_name, exclude_chat_id=target_id):
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Такое имя уже занято. Введи другое.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        set_user_registration_name(target_id, registration_name)
        set_admin_mode(None, None, [])
        send_text(SENDER_BOT_TOKEN, chat_id, f"Имя пользователя {target_id} обновлено: {registration_name}")
        try:
            send_text(
                RECEIVER_BOT_TOKEN,
                target_id,
                f"Администратор изменил твое имя регистрации на: {registration_name}",
                reply_markup=receiver_main_keyboard(),
            )
        except Exception:  # noqa: BLE001
            pass
        show_panel(chat_id)
        return True

    if mode == "ban_for_user":
        target_id = parse_chat_id(state.get("target_id"))
        if target_id is None:
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        if not get_user(target_id):
            send_text(SENDER_BOT_TOKEN, chat_id, "Пользователь не найден.")
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        until_utc, until_display, parse_error = parse_ban_until_input(text)
        if parse_error:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                parse_error,
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        set_user_banned(target_id, True, reason=f"temporary_until:{until_display}", until_at=until_utc)
        reset_runtime_state_for_user(target_id)
        try_notify_ban(target_id, until_display=until_display)
        set_admin_mode(None, None, [])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Пользователь {target_id} заблокирован до {until_display}.",
        )
        show_panel(chat_id)
        return True

    if mode == "add_friend_for_user":
        first_id = parse_chat_id(state.get("target_id"))
        if first_id is None:
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        if not get_user(first_id):
            send_text(SENDER_BOT_TOKEN, chat_id, "Первый пользователь не найден.")
            set_admin_mode(None, None, [])
            show_panel(chat_id)
            return True
        second_row = resolve_user_identifier(text)
        if not second_row:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Второй пользователь не найден. Пришли ID или @username.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        second_id = int(second_row["chat_id"])
        if first_id == second_id:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Нельзя добавить пользователя в друзья самому себе.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        if not is_user_registered(first_id) or not is_user_registered(second_id):
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Оба пользователя должны быть зарегистрированы.",
                reply_markup=admin_cancel_keyboard(),
            )
            return True
        create_friendship(first_id, second_id, created_by=chat_id)
        set_admin_mode(None, None, [])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Дружба добавлена: {first_id} <-> {second_id}",
        )
        try:
            first_row = get_user(first_id) or {"chat_id": first_id}
            second_full = get_user(second_id) or {"chat_id": second_id}
            send_text(
                RECEIVER_BOT_TOKEN,
                first_id,
                f"Администратор добавил тебе друга: {build_name(second_full)}",
                reply_markup=receiver_main_keyboard(),
            )
            send_text(
                RECEIVER_BOT_TOKEN,
                second_id,
                f"Администратор добавил тебе друга: {build_name(first_row)}",
                reply_markup=receiver_main_keyboard(),
            )
        except Exception:  # noqa: BLE001
            pass
        show_panel(chat_id)
        return True

    return False


def handle_sender_command(chat_id, command, args):
    if command in ("/panel", "/status"):
        show_panel(chat_id)
        return

    if command == "/help":
        send_text(SENDER_BOT_TOKEN, chat_id, admin_help_text(), reply_markup=admin_main_keyboard())
        return

    if command == "/cancel":
        set_admin_mode(None, None, [])
        show_panel(chat_id)
        return

    if command == "/users":
        if args.lower() == "all":
            rows = list_users(limit=200, offset=0, consent_only=True)
            if not rows:
                send_text(SENDER_BOT_TOKEN, chat_id, "Пользователи не найдены.")
                return
            lines = ["Зарегистрированные пользователи (all):"]
            for row in rows:
                lines.append(short_user_line(row))
            send_text(SENDER_BOT_TOKEN, chat_id, "\n".join(lines))
            return
        text, keyboard = build_users_page(0)
        send_text(SENDER_BOT_TOKEN, chat_id, text, reply_markup=keyboard)
        return

    if command == "/top":
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            top_users_text(),
            reply_markup={"inline_keyboard": [[{"text": "Меню", "callback_data": "adm:panel"}]]},
        )
        return

    if command == "/reports":
        text, keyboard = build_reports_page(0)
        send_text(SENDER_BOT_TOKEN, chat_id, text, reply_markup=keyboard)
        return

    if command == "/registrations":
        text, keyboard = build_registrations_page(0)
        send_text(SENDER_BOT_TOKEN, chat_id, text, reply_markup=keyboard)
        return

    if command == "/user":
        user_row = resolve_user_identifier(args)
        if not user_row:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /user <id|@username>")
            return
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            user_detail(user_row),
            reply_markup=build_user_keyboard(user_row, 0),
        )
        return

    if command == "/user_regs":
        user_row = resolve_user_identifier(args)
        if not user_row:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /user_regs <id|@username>")
            return
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            user_registration_events_text(user_row),
            reply_markup=build_user_keyboard(user_row, 0),
        )
        return

    if command == "/autoclean":
        if not args:
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                admin_autoclean_text(),
                reply_markup=admin_autoclean_keyboard(),
            )
            return
        seconds, parse_error = parse_autoclean_input(args)
        if parse_error:
            send_text(SENDER_BOT_TOKEN, chat_id, parse_error)
            return
        set_admin_autoclean_seconds(seconds)
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Автоочистка установлена: {format_duration(seconds)}",
            reply_markup=admin_autoclean_keyboard(),
        )
        return

    if command == "/setname":
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /setname <id|@username> <новое_имя>")
            return
        user_row = resolve_user_identifier(parts[0])
        if not user_row:
            send_text(SENDER_BOT_TOKEN, chat_id, "Пользователь не найден.")
            return
        target_id = int(user_row["chat_id"])
        registration_name, validation_error = validate_registration_name(parts[1].strip())
        if validation_error:
            send_text(SENDER_BOT_TOKEN, chat_id, validation_error)
            return
        if is_registration_name_taken(registration_name, exclude_chat_id=target_id):
            send_text(SENDER_BOT_TOKEN, chat_id, "Такое имя уже занято.")
            return
        set_user_registration_name(target_id, registration_name)
        send_text(SENDER_BOT_TOKEN, chat_id, f"Имя обновлено для {target_id}: {registration_name}")
        return

    if command == "/ban_for":
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /ban_for <id|@username> <время>")
            return
        user_row = resolve_user_identifier(parts[0])
        if not user_row:
            send_text(SENDER_BOT_TOKEN, chat_id, "Пользователь не найден.")
            return
        until_utc, until_display, parse_error = parse_ban_until_input(parts[1])
        if parse_error:
            send_text(SENDER_BOT_TOKEN, chat_id, parse_error)
            return
        target_id = int(user_row["chat_id"])
        set_user_banned(target_id, True, reason=f"temporary_until:{until_display}", until_at=until_utc)
        reset_runtime_state_for_user(target_id)
        try_notify_ban(target_id, until_display=until_display)
        send_text(SENDER_BOT_TOKEN, chat_id, f"Пользователь {target_id} в бане до {until_display}.")
        return

    if command == "/friend_add":
        left, right = parse_two_user_identifiers(args)
        if not left or not right:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /friend_add <id|@u> <id|@u>")
            return
        first_id = int(left["chat_id"])
        second_id = int(right["chat_id"])
        if first_id == second_id:
            send_text(SENDER_BOT_TOKEN, chat_id, "Нельзя добавить пользователя в друзья самому себе.")
            return
        if not is_user_registered(first_id) or not is_user_registered(second_id):
            send_text(SENDER_BOT_TOKEN, chat_id, "Оба пользователя должны быть зарегистрированы.")
            return
        create_friendship(first_id, second_id, created_by=chat_id)
        send_text(SENDER_BOT_TOKEN, chat_id, f"Дружба добавлена: {first_id} <-> {second_id}")
        return

    if command == "/friend_remove":
        left, right = parse_two_user_identifiers(args)
        if not left or not right:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /friend_remove <id|@u> <id|@u>")
            return
        first_id = int(left["chat_id"])
        second_id = int(right["chat_id"])
        removed = remove_friendship(first_id, second_id)
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            f"Связь удалена: {first_id} <-> {second_id}" if removed else "Связь уже отсутствует.",
        )
        return

    if command in ("/mute", "/unmute", "/remove", "/ban", "/unban"):
        user_row = resolve_user_identifier(args)
        if not user_row:
            send_text(SENDER_BOT_TOKEN, chat_id, f"Формат: {command} <id|@username>")
            return
        target_id = int(user_row["chat_id"])
        if command == "/remove":
            reset_runtime_state_for_user(target_id)
            notify_removed_account(target_id)
            remove_user(target_id)
            send_text(SENDER_BOT_TOKEN, chat_id, f"Пользователь {target_id} удален из базы.")
            return
        if command in ("/ban", "/unban"):
            banned = command == "/ban"
            set_user_banned(target_id, banned, reason="manual_admin_action" if banned else None)
            if banned:
                reset_runtime_state_for_user(target_id)
                try_notify_ban(target_id)
            state = "заблокирован" if banned else "разблокирован"
            send_text(SENDER_BOT_TOKEN, chat_id, f"Пользователь {target_id} {state}.")
            return
        enabled = command == "/unmute"
        set_broadcast_enabled(target_id, enabled)
        state = "включена" if enabled else "выключена"
        send_text(SENDER_BOT_TOKEN, chat_id, f"Рассылка для {target_id} {state}.")
        return

    if command == "/send":
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /send <id|@username> <текст>")
            return
        user_row = resolve_user_identifier(parts[0])
        message_text = parts[1].strip()
        if not user_row or not message_text:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /send <id|@username> <текст>")
            return
        perform_direct_send(chat_id, int(user_row["chat_id"]), message_text)
        return

    if command == "/broadcast":
        if not args:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /broadcast <текст>")
            return
        perform_broadcast(chat_id, args)
        return

    if command == "/broadcast_to":
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /broadcast_to <id|@u,id|@u> <текст>")
            return
        targets, unresolved = parse_target_identifiers_csv(parts[0])
        message_text = parts[1].strip()
        if not targets or not message_text:
            send_text(SENDER_BOT_TOKEN, chat_id, "Формат: /broadcast_to <id|@u,id|@u> <текст>")
            return
        delivered, failed = send_to_targets(message_text, targets)
        unresolved_text = ", ".join(unresolved) if unresolved else "-"
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            (
                "Выборочная рассылка завершена.\n"
                f"Целей: {len(targets)}\n"
                f"Доставлено: {delivered}\n"
                f"Ошибок: {failed}\n"
                f"Не найдены: {unresolved_text}"
            ),
        )
        return

    send_text(SENDER_BOT_TOKEN, chat_id, admin_help_text())


def handle_sender_message(message):
    chat = message.get("chat", {})
    if chat.get("type") != "private":
        return

    chat_id = chat.get("id")
    user = message.get("from", {})
    user_id = user.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None or user_id is None:
        return

    command, args = split_command(text) if text else ("", "")

    if command == "/start":
        begin_admin_auth(user_id)
        set_admin_mode(None, None, [])
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Введите пароль для входа в админ-панель.",
        )
        send_text(SENDER_BOT_TOKEN, chat_id, admin_password_prompt(1))
        return

    auth_stage = get_admin_auth_stage(user_id)
    if auth_stage is not None:
        if not text:
            send_text(SENDER_BOT_TOKEN, chat_id, admin_password_prompt(auth_stage))
            return
        if text.startswith("/"):
            send_text(
                SENDER_BOT_TOKEN,
                chat_id,
                "Сейчас нужно ввести пароль цифрами. Или нажми /start заново.",
            )
            return
        handle_admin_password_input(chat_id, user_id, text)
        return

    if not is_admin_session_allowed(user_id):
        send_text(
            SENDER_BOT_TOKEN,
            chat_id,
            "Доступ закрыт. Нажми /start и введи пароль 3 раза.",
        )
        return

    if command:
        handle_sender_command(chat_id, command, args)
        return

    if not text:
        send_text(SENDER_BOT_TOKEN, chat_id, "Отправь текст или команду /help.")
        return

    if handle_sender_mode(chat_id, text):
        return

    perform_broadcast(chat_id, text)


def handle_sender_update(update):
    callback_query = update.get("callback_query")
    if callback_query:
        handle_sender_callback(callback_query)
        return
    message = update.get("message")
    if message:
        handle_sender_message(message)


def poll_loop(name, token, offset_key, handler, allowed_updates):
    offset = get_offset(offset_key)
    print(f"[{name}] polling started with offset={offset}")
    last_admin_cleanup_at = 0.0

    while not stop_event.is_set():
        try:
            if name == "sender":
                now_ts = time.time()
                if now_ts - last_admin_cleanup_at >= 60.0:
                    admin_id = get_admin_id()
                    if admin_id is not None:
                        try:
                            maybe_cleanup_admin_chat(admin_id, limit=120)
                        except Exception:  # noqa: BLE001
                            pass
                    last_admin_cleanup_at = now_ts
            updates = get_updates(token, offset, allowed_updates)
            if not updates:
                continue
            for update in updates:
                update_id = update.get("update_id")
                if update_id is None:
                    continue
                offset = int(update_id) + 1
                set_offset(offset_key, offset)
                try:
                    handler(update)
                except Exception as exc:  # noqa: BLE001
                    print(f"[{name}] handler error: {exc}")
        except TelegramApiError as exc:
            print(f"[{name}] Telegram API error: {exc}")
            time.sleep(RETRY_DELAY)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"[{name}] network error: {exc}")
            time.sleep(RETRY_DELAY)
        except Exception as exc:  # noqa: BLE001
            print(f"[{name}] unexpected error: {exc}")
            time.sleep(RETRY_DELAY)

    print(f"[{name}] polling stopped")


def validate_tokens():
    sender_me = tg_api(SENDER_BOT_TOKEN, "getMe")
    receiver_me = tg_api(RECEIVER_BOT_TOKEN, "getMe")
    sender_name = sender_me.get("username", "unknown")
    receiver_name = receiver_me.get("username", "unknown")
    print(f"Sender bot: @{sender_name}")
    print(f"Receiver bot: @{receiver_name}")


def shutdown_handler(signum, _frame):
    print(f"Signal {signum} received, stopping...")
    stop_event.set()


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = (self.path or "/").split("?", 1)[0]
        if path in {"/", "/health", "/ping"}:
            payload = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, _format, *_args):
        return


def parse_int_env(name, default, min_value, max_value):
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    if parsed < min_value:
        return min_value
    if parsed > max_value:
        return max_value
    return parsed


def start_health_server_thread():
    port_raw = os.getenv("PORT", "").strip()
    if not port_raw:
        return None
    try:
        port = int(port_raw)
    except ValueError:
        print(f"[health] invalid PORT value: {port_raw}")
        return None
    if port < 1 or port > 65535:
        print(f"[health] invalid PORT range: {port}")
        return None

    def _run_health_server():
        try:
            server = http.server.ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
            server.timeout = 1
        except Exception as exc:  # noqa: BLE001
            print(f"[health] failed to start HTTP server: {exc}")
            return
        print(f"[health] listening on 0.0.0.0:{port}")
        while not stop_event.is_set():
            server.handle_request()
        server.server_close()
        print("[health] stopped")

    thread = threading.Thread(target=_run_health_server, daemon=True)
    thread.start()
    return thread


def resolve_keepalive_url():
    explicit = os.getenv("KEEPALIVE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip()
    if render_url:
        return render_url.rstrip("/")
    return ""


def start_self_ping_thread():
    keepalive_url = resolve_keepalive_url()
    if not keepalive_url:
        return None
    interval = parse_int_env("KEEPALIVE_INTERVAL_SECONDS", 480, 120, 1800)

    def _run_self_ping():
        ping_url = f"{keepalive_url}/health"
        print(f"[health] self ping enabled: {ping_url} every {interval}s")
        if stop_event.wait(30):
            print("[health] self ping stopped")
            return
        while not stop_event.is_set():
            try:
                request = urllib.request.Request(ping_url, method="GET")
                with urllib.request.urlopen(request, timeout=12):
                    pass
            except Exception as exc:  # noqa: BLE001
                print(f"[health] self ping error: {exc}")
            if stop_event.wait(interval):
                break
        print("[health] self ping stopped")

    thread = threading.Thread(target=_run_self_ping, daemon=True)
    thread.start()
    return thread


def main():
    global SENDER_BOT_TOKEN, RECEIVER_BOT_TOKEN, ADMIN_PASSWORD, SSL_CONTEXT

    load_env(ENV_PATH)
    SENDER_BOT_TOKEN = os.getenv("SENDER_BOT_TOKEN", "").strip()
    RECEIVER_BOT_TOKEN = os.getenv("RECEIVER_BOT_TOKEN", "").strip()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD).strip() or DEFAULT_ADMIN_PASSWORD
    if os.getenv("TG_INSECURE_SSL", "").strip().lower() in {"1", "true", "yes"}:
        SSL_CONTEXT = ssl._create_unverified_context()

    if not SENDER_BOT_TOKEN or not RECEIVER_BOT_TOKEN:
        raise SystemExit("Missing SENDER_BOT_TOKEN or RECEIVER_BOT_TOKEN in .env")

    init_db()
    validate_tokens()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    health_thread = start_health_server_thread()
    self_ping_thread = start_self_ping_thread()

    sender_thread = threading.Thread(
        target=poll_loop,
        args=("sender", SENDER_BOT_TOKEN, SENDER_BOT_KEY, handle_sender_update, ["message", "callback_query"]),
        daemon=True,
    )
    receiver_thread = threading.Thread(
        target=poll_loop,
        args=(
            "receiver",
            RECEIVER_BOT_TOKEN,
            RECEIVER_BOT_KEY,
            handle_receiver_update,
            ["message", "callback_query"],
        ),
        daemon=True,
    )

    sender_thread.start()
    receiver_thread.start()

    print("Both bots are running. Press Ctrl+C to stop.")
    while not stop_event.is_set():
        time.sleep(0.5)

    sender_thread.join(timeout=2)
    receiver_thread.join(timeout=2)
    if health_thread is not None:
        health_thread.join(timeout=2)
    if self_ping_thread is not None:
        self_ping_thread.join(timeout=2)
    if db is not None:
        db.close()
    print("Stopped.")


if __name__ == "__main__":
    main()
