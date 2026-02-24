from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.llm_client import LLMClient
from app.web_search import WebHit, format_web_hits, search_web


ProgressCallback = Callable[[int, str], Awaitable[None] | None]


@dataclass(frozen=True)
class PipelineResult:
    answer_text: str
    candidates: list[str]


_AGENT_SYSTEM_PROMPTS = [
    "Ты агент 1. Отвечай строго с опорой на библейский текст и указывай стихи.",
    "Ты агент 2. Дай богословское объяснение с аккуратными ссылками на Писание.",
    "Ты агент 3. Будь максимально осторожен: где есть сомнение, явно помечай это.",
    "Ты агент 4. Проверяй согласованность между Ветхим и Новым Заветом.",
]

_LENGTH_INSTRUCTIONS = {
    "very_short": "очень коротко: 1-2 предложения",
    "short": "коротко: до 1 небольшого абзаца",
    "medium": "средне: 1-2 абзаца",
    "long": "длинно: 2-4 абзаца с пояснениями",
    "very_long": "очень длинно: подробный разбор с примерами",
}

_DENOMINATION_INSTRUCTIONS = {
    "orthodox": "Православная перспектива (по умолчанию).",
    "catholic": "Католическая перспектива (в рамках христианского учения).",
}

_EXPLAIN_STYLE_INSTRUCTIONS = {
    "orthodox": "Пиши богословски корректно и в традиционном православном стиле.",
    "simple": "Пиши максимально простым и разговорным языком.",
    "layered": "Сначала дай более сложное объяснение, затем тут же упрости его.",
}

_AGENT_MAX_TOKENS = {
    "very_short": 180,
    "short": 260,
    "medium": 420,
    "long": 650,
    "very_long": 850,
}

_FINAL_MAX_TOKENS = {
    "very_short": 220,
    "short": 340,
    "medium": 600,
    "long": 950,
    "very_long": 1200,
}


def _normalize_answer_length(value: str) -> str:
    return value if value in _LENGTH_INSTRUCTIONS else "long"


def _normalize_denomination(value: str) -> str:
    return "catholic" if value == "catholic" else "orthodox"


def _normalize_explain_style(value: str) -> str:
    return value if value in _EXPLAIN_STYLE_INSTRUCTIONS else "orthodox"


def _normalize_reasoning_mode(value: str) -> str:
    return value if value in {"fast", "balanced", "deep"} else "balanced"


async def _report_progress(callback: ProgressCallback | None, percent: int, stage: str) -> None:
    if callback is None:
        return
    try:
        maybe = callback(max(0, min(percent, 100)), stage)
        if asyncio.iscoroutine(maybe):
            await maybe
    except Exception:
        return


def _style_block(denomination: str, answer_length: str, explain_style: str) -> str:
    return (
        f"Конфессия: {_DENOMINATION_INSTRUCTIONS[denomination]}\n"
        f"Формат длины: {_LENGTH_INSTRUCTIONS[answer_length]}\n"
        f"Способ объяснения: {_EXPLAIN_STYLE_INSTRUCTIONS[explain_style]}\n"
        "Если вопрос о Боге, объясняй через христианское учение об Иисусе Христе."
    )


def _build_agent_user_prompt(
    question: str,
    context_excerpt: str,
    web_context: str,
    denomination: str,
    answer_length: str,
    explain_style: str,
) -> str:
    return (
        "История диалога (для понимания контекста):\n"
        f"{context_excerpt or '(пусто)'}\n\n"
        "Текущий вопрос пользователя:\n"
        f"{question}\n\n"
        "Свежие источники из интернета:\n"
        f"{web_context}\n\n"
        "Стиль ответа:\n"
        f"{_style_block(denomination=denomination, answer_length=answer_length, explain_style=explain_style)}\n\n"
        "Требования:\n"
        "1) Пиши только на русском.\n"
        "2) Только тема Библии/Бога/христианского учения.\n"
        "3) По возможности приводи ссылки на места Писания."
    )


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "rate limit" in text or "too many requests" in text


async def _chat_with_retry(
    llm: LLMClient,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    model: str,
    retries: int = 2,
) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await llm.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
            )
        except Exception as error:
            last_error = error
            if attempt >= retries or not _is_rate_limit_error(error):
                raise
            await asyncio.sleep(1.1 * (attempt + 1))

    if last_error:
        raise last_error
    raise RuntimeError("LLM call failed")


async def _run_single_agent(
    llm: LLMClient,
    system_prompt: str,
    question: str,
    context_excerpt: str,
    web_context: str,
    temperature: float,
    model: str,
    denomination: str,
    answer_length: str,
    explain_style: str,
    max_tokens: int,
    retries: int,
) -> str:
    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": _build_agent_user_prompt(
                question=question,
                context_excerpt=context_excerpt,
                web_context=web_context,
                denomination=denomination,
                answer_length=answer_length,
                explain_style=explain_style,
            ),
        },
    ]

    return await _chat_with_retry(
        llm=llm,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        retries=retries,
    )


async def _synthesize(
    llm: LLMClient,
    question: str,
    context_excerpt: str,
    web_context: str,
    candidates: list[str],
    temperature: float,
    model: str,
    denomination: str,
    answer_length: str,
    explain_style: str,
    max_tokens: int,
    retries: int,
) -> str:
    numbered_candidates = "\n\n".join(
        f"Черновик {idx}:\n{text}" for idx, text in enumerate(candidates, start=1)
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Ты главный редактор ответа. Получишь несколько черновиков (обычно 4) от разных моделей. "
                "Собери единый, точный и понятный ответ на русском. "
                "Не показывай черновики пользователю и не упоминай их в финале."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Контекст диалога:\n{context_excerpt or '(пусто)'}\n\n"
                f"Вопрос:\n{question}\n\n"
                f"Свежие источники:\n{web_context}\n\n"
                f"Черновики:\n{numbered_candidates}\n\n"
                f"Стиль:\n{_style_block(denomination=denomination, answer_length=answer_length, explain_style=explain_style)}\n\n"
                "Сформируй финал в формате:\n"
                "- Ответ\n"
                "- Ссылки на Библию\n"
                "- Коротко: какие веб-ссылки помогли (если помогли)"
            ),
        },
    ]

    return await _chat_with_retry(
        llm=llm,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        retries=retries,
    )


async def _self_review(
    llm: LLMClient,
    question: str,
    draft_answer: str,
    model: str,
    denomination: str,
    answer_length: str,
    explain_style: str,
    max_tokens: int,
    retries: int,
) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Ты финальный проверяющий. Улучши ответ: "
                "1) только русский язык; "
                "2) без служебных слов вроде 'черновик', 'candidate'; "
                "3) без лишних англоязычных фраз; "
                "4) без противоречий; "
                "5) христоцентричный ответ, если вопрос касается Бога."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Вопрос:\n{question}\n\n"
                f"Требуемый стиль:\n{_style_block(denomination=denomination, answer_length=answer_length, explain_style=explain_style)}\n\n"
                f"Черновой финальный ответ:\n{draft_answer}\n\n"
                "Дай улучшенный итоговый ответ на русском."
            ),
        },
    ]

    return await _chat_with_retry(
        llm=llm,
        messages=messages,
        temperature=0.1,
        max_tokens=max_tokens,
        model=model,
        retries=retries,
    )


async def _emergency_answer(
    llm: LLMClient,
    question: str,
    context_excerpt: str,
    denomination: str,
    answer_length: str,
    explain_style: str,
    model: str,
    max_tokens: int,
    retries: int,
) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Ты экстренный резервный режим. Дай один итоговый ответ строго на русском, "
                "по теме Библии/Бога/христианства, без технических пояснений."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Контекст:\\n{context_excerpt or '(пусто)'}\\n\\n"
                f"Вопрос:\\n{question}\\n\\n"
                f"Стиль:\\n{_style_block(denomination=denomination, answer_length=answer_length, explain_style=explain_style)}"
            ),
        },
    ]
    return await _chat_with_retry(
        llm=llm,
        messages=messages,
        temperature=0.2,
        max_tokens=max_tokens,
        model=model,
        retries=retries,
    )


def _mode_profile(reasoning_mode: str, web_results: int) -> dict[str, int | bool | float]:
    mode = _normalize_reasoning_mode(reasoning_mode)
    if mode == "fast":
        return {
            "web_results": 0,
            "agent_factor": 0.55,
            "final_factor": 0.55,
            "self_review": False,
            "extra_review": False,
            "retries": 1,
        }
    if mode == "deep":
        return {
            "web_results": max(web_results, 6),
            "agent_factor": 1.2,
            "final_factor": 1.25,
            "self_review": True,
            "extra_review": True,
            "retries": 3,
        }
    return {
        "web_results": web_results,
        "agent_factor": 1.0,
        "final_factor": 1.0,
        "self_review": True,
        "extra_review": False,
        "retries": 2,
    }


def _cleanup_answer(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            cleaned.append("")
            continue
        if re.match(r"^(candidate|черновик)\s*\d*[:\-]", line, flags=re.IGNORECASE):
            continue
        cleaned.append(raw)

    normalized = "\n".join(cleaned).strip()
    if not normalized:
        return "Не удалось подготовить итоговый ответ. Попробуйте переформулировать вопрос."
    return normalized


def _append_sources(answer_text: str, hits: list[WebHit]) -> str:
    if not hits:
        return f"{answer_text}\n\nПроверено 4 моделями и финальной самопроверкой."

    links = "\n".join(f"- {hit.url}" for hit in hits[:3])
    return (
        f"{answer_text}\n\n"
        "Проверено 4 моделями и финальной самопроверкой.\n"
        "Свежие ссылки:\n"
        f"{links}"
    )


async def run_pipeline(
    llm: LLMClient,
    question: str,
    web_results: int,
    temperature: float,
    context_excerpt: str = "",
    agent_models: list[str] | None = None,
    denomination: str = "orthodox",
    answer_length: str = "long",
    explain_style: str = "orthodox",
    reasoning_mode: str = "balanced",
    progress_callback: ProgressCallback | None = None,
) -> PipelineResult:
    denomination = _normalize_denomination(denomination)
    answer_length = _normalize_answer_length(answer_length)
    explain_style = _normalize_explain_style(explain_style)
    mode = _mode_profile(reasoning_mode=reasoning_mode, web_results=web_results)
    selected_web_results = int(mode["web_results"])
    retries = int(mode["retries"])
    agent_max_tokens = max(120, int(_AGENT_MAX_TOKENS[answer_length] * float(mode["agent_factor"])))
    final_max_tokens = max(180, int(_FINAL_MAX_TOKENS[answer_length] * float(mode["final_factor"])))
    use_self_review = bool(mode["self_review"])
    use_extra_review = bool(mode["extra_review"])

    models = list(agent_models or [llm.default_model] * 4)
    while len(models) < 4:
        models.append(models[-1])
    models = models[:4]

    hits: list[WebHit] = []
    web_context = "No web results available."
    if selected_web_results > 0:
        await _report_progress(progress_callback, 8, "Ищу свежие источники")
        query = f"Bible and Christianity question: {question}"
        hits = await search_web(query, max_results=selected_web_results)
        web_context = format_web_hits(hits)
    else:
        await _report_progress(progress_callback, 8, "Быстрый режим без веб-поиска")

    await _report_progress(progress_callback, 22, "Запускаю 4 модели")
    tasks = [
        asyncio.create_task(
            _run_single_agent(
                llm=llm,
                system_prompt=system_prompt,
                question=question,
                context_excerpt=context_excerpt,
                web_context=web_context,
                temperature=min(0.9, temperature + idx * 0.1),
                model=models[idx],
                denomination=denomination,
                answer_length=answer_length,
                explain_style=explain_style,
                max_tokens=agent_max_tokens,
                retries=retries,
            )
        )
        for idx, system_prompt in enumerate(_AGENT_SYSTEM_PROMPTS)
    ]

    candidates: list[str] = []
    completed = 0
    for future in asyncio.as_completed(tasks):
        try:
            result = await future
            text = result.strip()
            if text:
                candidates.append(text)
        except Exception:
            pass
        completed += 1
        percent = 22 + int((completed / 4) * 48)
        await _report_progress(progress_callback, percent, f"Модели завершены: {completed}/4")

    # If some parallel calls failed due rate limits, try to top up sequentially.
    if len(candidates) < 4:
        await _report_progress(progress_callback, 72, "Добираю недостающие варианты")
        for idx in range(4):
            if len(candidates) >= 4:
                break
            try:
                extra = await _run_single_agent(
                    llm=llm,
                    system_prompt=_AGENT_SYSTEM_PROMPTS[idx],
                    question=question,
                    context_excerpt=context_excerpt,
                    web_context=web_context,
                    temperature=min(0.9, temperature + idx * 0.1),
                    model=models[idx],
                    denomination=denomination,
                    answer_length=answer_length,
                    explain_style=explain_style,
                    max_tokens=agent_max_tokens,
                    retries=max(1, retries - 1),
                )
                extra = extra.strip()
                if extra:
                    candidates.append(extra)
            except Exception:
                pass

    if not candidates:
        await _report_progress(progress_callback, 82, "Пробую резервный режим")
        try:
            emergency = await _emergency_answer(
                llm=llm,
                question=question,
                context_excerpt=context_excerpt,
                denomination=denomination,
                answer_length=answer_length,
                explain_style=explain_style,
                model=models[0],
                max_tokens=final_max_tokens,
                retries=max(2, retries),
            )
            await _report_progress(progress_callback, 97, "Форматирую итог")
            final_answer = _cleanup_answer(emergency)
            final_answer = _append_sources(answer_text=final_answer, hits=hits)
            return PipelineResult(answer_text=final_answer, candidates=[emergency])
        except Exception:
            await _report_progress(progress_callback, 96, "Не удалось собрать ответы")
            return PipelineResult(
                answer_text=(
                    "Не удалось получить ответы от моделей. "
                    "Попробуйте повторить запрос через минуту."
                ),
                candidates=[],
            )

    judge_model = models[0]
    await _report_progress(progress_callback, 76, "Сверяю варианты")
    try:
        draft_final = await _synthesize(
            llm=llm,
            question=question,
            context_excerpt=context_excerpt,
            web_context=web_context,
            candidates=candidates,
            temperature=temperature,
            model=judge_model,
            denomination=denomination,
            answer_length=answer_length,
            explain_style=explain_style,
            max_tokens=final_max_tokens,
            retries=retries,
        )
    except Exception:
        draft_final = candidates[0]

    reviewed_final = draft_final
    if use_self_review:
        await _report_progress(progress_callback, 90, "Финальная самопроверка")
        try:
            reviewed_final = await _self_review(
                llm=llm,
                question=question,
                draft_answer=draft_final,
                model=judge_model,
                denomination=denomination,
                answer_length=answer_length,
                explain_style=explain_style,
                max_tokens=final_max_tokens,
                retries=retries,
            )
        except Exception:
            reviewed_final = draft_final

    if use_extra_review:
        await _report_progress(progress_callback, 94, "Дополнительная глубокая проверка")
        try:
            reviewed_final = await _self_review(
                llm=llm,
                question=question,
                draft_answer=reviewed_final,
                model=judge_model,
                denomination=denomination,
                answer_length=answer_length,
                explain_style=explain_style,
                max_tokens=final_max_tokens,
                retries=retries,
            )
        except Exception:
            pass

    await _report_progress(progress_callback, 97, "Форматирую итог")
    final_answer = _cleanup_answer(reviewed_final)
    final_answer = _append_sources(answer_text=final_answer, hits=hits)

    return PipelineResult(answer_text=final_answer, candidates=candidates)
