from __future__ import annotations

import re

from app.llm_client import LLMClient


RULE_VIOLATION_TEXT = (
    "Этот бот отвечает только на вопросы о Библии, Боге и христианском учении. "
    "Ваш запрос противоречит правилам."
)


_BIBLE_PATTERNS = [
    re.compile(r"\bбибли\w*", re.IGNORECASE),
    re.compile(r"\b(ветхий|новый)\s+завет", re.IGNORECASE),
    re.compile(r"\b(иисус|христ|бог|господь|яхве|святой\s+дух)\b", re.IGNORECASE),
    re.compile(r"\b(евангелие|апостол|пророк|псалом|притч|бытие|исход|левит|числа|второзаконие)\b", re.IGNORECASE),
    re.compile(r"\b(молитв\w*|грех\w*|покаян\w*|благодат\w*|спасен\w*|церков\w*)\b", re.IGNORECASE),
    re.compile(r"\b(матфе[йя]|марк|лука|иоанн|деяния|римлянам|коринфянам|галатам|ефесянам)\b", re.IGNORECASE),
    re.compile(r"\b(genesis|exodus|leviticus|numbers|deuteronomy|psalm|psalms|proverbs|matthew|mark|luke|john|acts|romans)\b", re.IGNORECASE),
]

_FOLLOWUP_START = re.compile(r"^(а|и|но|ну|тогда|то|как|почему|зачем|где|когда|кто|что|он|она|они|это|этот|тот)\b", re.IGNORECASE)


def _looks_like_bible_question(question: str) -> bool:
    text = question.strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _BIBLE_PATTERNS)


def _looks_like_followup(question: str) -> bool:
    text = question.strip()
    if not text:
        return False

    if _FOLLOWUP_START.search(text):
        return True

    words = re.findall(r"[\wа-яА-ЯёЁ-]+", text)
    return 1 <= len(words) <= 8


async def is_bible_question(
    question: str,
    llm: LLMClient,
    context_excerpt: str = "",
    last_topic_bible: bool = False,
    model: str | None = None,
) -> bool:
    if _looks_like_bible_question(question):
        return True

    if last_topic_bible and _looks_like_followup(question):
        return True

    classifier_messages = [
        {
            "role": "system",
            "content": (
                "You are a strict classifier. Decide whether the latest user message is about the Bible, "
                "God, or Christian theology related to Biblical teaching. "
                "Use previous context to resolve pronouns and short follow-ups. "
                "Answer ONLY YES or NO."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Previous context:\n{context_excerpt or '(none)'}\n\n"
                f"Latest message:\n{question}"
            ),
        },
    ]

    try:
        answer = await llm.chat(
            classifier_messages,
            temperature=0.0,
            max_tokens=24,
            model=model,
        )
    except Exception:
        try:
            answer = await llm.chat(classifier_messages, temperature=0.0, max_tokens=24)
        except Exception:
            return False

    token = answer.strip().split(maxsplit=1)[0].strip(".,:;!?").upper() if answer.strip() else "NO"
    return token in {"YES", "ДА"}
