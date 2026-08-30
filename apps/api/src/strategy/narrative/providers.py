"""LLM provider 선택 층 — **어느 provider 를 쓸지는 코드가 아니라 설정이 정한다.**

★왜 생겼나 — 종전에는 「anthropic 우선 → gemini fallback」이 `narrative/service.py` 와
`generate_service.py` **양쪽에 복제**돼 있었고, 그 사실이 `AGENTS.md` 에도 하드코딩돼 있었다.
그런데 **환경마다 가진 키가 다르다**(2026-08-28 실측: 로컬은 openai 200 · gemini 400 ·
anthropic 401 · 서버는 셋 다 비어 있음). provider 를 늘릴 때마다 분기를 두 곳에 또 복제하는
대신 순서를 설정(`LLM_PROVIDER_ORDER`)으로 빼고 호출부를 하나로 모은다.

★**세 provider 모두 스키마를 강제한다.** 프롬프트로 형식을 부탁하면 모델이 안 지킬 수 있지만
SDK 스키마는 지킨다. `convert/service.py`도 같은 `complete_json` 계약을 사용한다.

| provider | 강제 수단 | 비고 |
| --- | --- | --- |
| anthropic | tool use + `tool_choice` 고정 | 도구 응답이 없으면 실패로 본다 |
| openai | Structured Outputs (`strict: true`) | 제약 디코딩이라 스키마 위반이 구조적으로 불가능 |
| gemini | `response_mime_type` + `response_schema` | |

★**[BL-772] 계약** — provider 예외 문자열(엔드포인트·모델·요청 ID)을 위로 흘리지 않는다.
상세는 `logger.exception` 으로 로그에만 남고, 호출자는 provider 중립 `RuntimeError` 만 본다.
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic
from google import genai
from google.genai import types as genai_types
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.config import Settings

logger = logging.getLogger(__name__)

_ANTHROPIC_TRANSIENT = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

KNOWN_PROVIDERS = ("anthropic", "openai", "gemini")


@dataclass(frozen=True)
class JsonCompletion:
    """공통 structured completion 결과.

    호출자는 성공한 provider와 실제 SDK usage를 함께 받아야 한다. payload만 반환하면
    fallback 뒤의 provider를 추측하게 되고, convert처럼 사용량을 응답 계약에 싣는
    호출부는 provider별 SDK를 다시 알아야 한다.
    """

    payload: dict[str, Any]
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0


def secret(value: Any) -> str:
    """`SecretStr | str | None` 에서 문자열을 꺼낸다. 없으면 빈 문자열."""
    if value is None:
        return ""
    getter = getattr(value, "get_secret_value", None)
    return (getter() if callable(getter) else str(value)) or ""


def provider_order(settings: Settings) -> list[str]:
    """설정의 쉼표 목록을 파싱한다. 모르는 이름은 조용히 버린다(오타가 전체를 막지 않게)."""
    raw = getattr(settings, "llm_provider_order", "") or ""
    seen: list[str] = []
    for name in (p.strip().lower() for p in raw.split(",")):
        if name in KNOWN_PROVIDERS and name not in seen:
            seen.append(name)
    return seen or list(KNOWN_PROVIDERS)


def _key_for(settings: Settings, name: str) -> str:
    return secret(getattr(settings, f"{name}_api_key", None))


def available_providers(settings: Settings) -> list[str]:
    """순서대로, **키가 있는** provider 만."""
    return [p for p in provider_order(settings) if _key_for(settings, p)]


def _strict(schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI Structured Outputs 의 strict 모드 요구를 만족시킨다.

    ★모든 object 에 `additionalProperties: false` 가 있어야 하고 모든 property 가 `required`
    여야 한다. 다른 두 provider 는 이 제약이 없지만 **같은 스키마를 셋이 공유**하도록
    여기서 한 번만 채운다 — 스키마가 갈라지면 provider 마다 다른 모양이 온다.
    """
    out = copy.deepcopy(schema)

    def walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            props = node.get("properties") or {}
            node["additionalProperties"] = False
            node["required"] = list(props.keys())
            for v in props.values():
                walk(v)
        if node.get("type") == "array":
            walk(node.get("items"))

    walk(out)
    return out


# ── provider 별 어댑터 ────────────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type(_ANTHROPIC_TRANSIENT),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _call_anthropic(
    settings: Settings, *, system: str, user: str, schema: dict[str, Any], tool_name: str
) -> JsonCompletion:
    client = anthropic.Anthropic(api_key=_key_for(settings, "anthropic"))
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=system,
        tools=[
            {"name": tool_name, "description": "구조화 결과를 보고합니다.", "input_schema": schema}
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )
    for block in response.content or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == tool_name:
            payload = getattr(block, "input", None)
            if isinstance(payload, dict):
                usage = getattr(response, "usage", None)
                return JsonCompletion(
                    payload=payload,
                    provider="anthropic",
                    input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                    output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                )
    # ★빈 결과를 성공으로 내면 화면이 침묵으로 거짓말한다.
    raise RuntimeError("도구 호출 응답이 오지 않았습니다")


def _call_openai(
    settings: Settings, *, system: str, user: str, schema: dict[str, Any], tool_name: str
) -> JsonCompletion:
    client = OpenAI(api_key=_key_for(settings, "openai"))
    response = client.chat.completions.create(
        model=settings.openai_model,
        max_completion_tokens=4096,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": tool_name, "schema": _strict(schema), "strict": True},
        },
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    choice = response.choices[0] if response.choices else None
    # ★strict 모드에서도 길이 초과로 잘릴 수 있다. 그때 부분 JSON 을 성공으로 내면 안 된다.
    if choice and getattr(choice, "finish_reason", None) == "length":
        raise RuntimeError("응답이 길이 상한에서 잘렸습니다")
    content = (choice.message.content if choice and choice.message else None) or ""
    payload = json.loads(content or "{}")
    if not isinstance(payload, dict):
        raise RuntimeError("JSON 객체가 아닙니다")
    usage = getattr(response, "usage", None)
    return JsonCompletion(
        payload=payload,
        provider="openai",
        input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
    )


def _call_gemini(
    settings: Settings, *, system: str, user: str, schema: dict[str, Any], tool_name: str
) -> JsonCompletion:
    client = genai.Client(api_key=_key_for(settings, "gemini"))
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=4096,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    payload = json.loads(response.text or "{}")
    if not isinstance(payload, dict):
        raise RuntimeError("JSON 객체가 아닙니다")
    usage = getattr(response, "usage_metadata", None)
    return JsonCompletion(
        payload=payload,
        provider="gemini",
        input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
        output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
    )


_ADAPTERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "gemini": _call_gemini,
}


def complete_json(
    settings: Settings,
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
    tool_name: str,
) -> JsonCompletion:
    """설정 순서대로 시도해 provider·usage를 포함한 구조화 결과를 돌려준다.

    키가 없는 provider 는 건너뛰고, 실패하면 다음으로 넘어간다. 전부 실패하면 RuntimeError.
    ★provider 예외 문자열은 **로그에만** 남는다([BL-772]).
    """
    candidates = available_providers(settings)
    if not candidates:
        raise RuntimeError(
            "사용 가능한 LLM provider 가 없습니다. "
            "ANTHROPIC_API_KEY · OPENAI_API_KEY · GEMINI_API_KEY 중 하나를 설정하세요"
        )

    for name in candidates:
        try:
            return _ADAPTERS[name](
                settings, system=system, user=user, schema=schema, tool_name=tool_name
            )
        except Exception as exc:
            logger.exception(
                "llm provider failed provider=%s exc_type=%s", name, type(exc).__name__
            )

    raise RuntimeError("LLM provider 를 사용할 수 없습니다")
