"""LLM provider 의 **살아 있는 모델 목록**을 읽어 하나의 모양으로 정규화한다.

★왜 있나 — 2026-08-28 에 기본값 `gemini-2.0-flash` 가 **폐기돼 404** 를 내고 있었고, 그 사실을
아무 테스트도 못 잡았다(전송을 mock 하므로 죽은 id 도 통과한다). 설정한 모델이 provider 의
**실제 목록에 있는지**는 물어봐야만 알 수 있다.

★이 모듈이 **판정하지 않는 것** — 「목록에 있다」는 「우리 호출 모양으로 동작한다」가 아니다.
같은 날 실측: `gemini-3.7-flash` 는 목록에 **있는데** 503 을 낸다. OpenAI 목록에는 애초에
capability 필드가 **없어서**(`id`·`created`·`shutdown_date` 뿐) chat 가능 여부를 이름으로
추측할 수밖에 없다. 그래서 이 모듈은 **후보를 좁혀 줄 뿐 보증하지 않는다.**
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from src.core.config import Settings
from src.strategy.narrative.providers import KNOWN_PROVIDERS, provider_order, secret

logger = logging.getLogger(__name__)

# 목록은 자주 안 바뀌는데 provider 왕복 3회는 비싸다. 프로세스 안에서만 산다.
_TTL_SECONDS = 900
_cache: dict[str, tuple[float, ProviderCatalog]] = {}

# ★OpenAI 목록에는 capability 필드가 없다 — 이름으로 거르는 **추측**이고 그렇게 표기한다.
#   chat/completions 를 못 받는 것이 확실한 계열만 뺀다(과하게 빼면 쓸 모델이 사라진다).
_OPENAI_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt-")
_OPENAI_NON_CHAT_MARKERS = (
    "-instruct",
    "-realtime",
    "-audio",
    "-transcribe",
    "-tts",
    "tts-",
    "-search",
    "-image",
    "-moderation",
    "embedding",
    "whisper",
    "dall-e",
    "-codex",
)


@dataclass(frozen=True)
class ModelInfo:
    id: str
    display_name: str | None = None
    shutdown_date: str | None = None
    input_token_limit: int | None = None
    output_token_limit: int | None = None


@dataclass
class ProviderCatalog:
    provider: str
    models: list[ModelInfo] = field(default_factory=list)
    total_seen: int = 0
    configured: str | None = None
    error: str | None = None

    @property
    def configured_listed(self) -> bool | None:
        """설정된 모델이 목록에 있나. 목록을 못 읽었으면 **모른다**(None) — False 가 아니다."""
        if self.error is not None or self.configured is None:
            return None
        return any(m.id == self.configured for m in self.models)


def _openai_is_chat(model_id: str) -> bool:
    low = model_id.lower()
    if not low.startswith(_OPENAI_CHAT_PREFIXES):
        return False
    return not any(mark in low for mark in _OPENAI_NON_CHAT_MARKERS)


def _fetch_openai(settings: Settings) -> tuple[list[ModelInfo], int]:
    from openai import OpenAI

    # ★클라이언트를 **지역 변수로 붙잡는다.** 인라인으로 쓰면 지연 pager 가 다음 페이지를
    #   받기 전에 GC 되어 httpx 가 닫히고 `RuntimeError: client has been closed` 가 난다
    #   (2026-08-28 gemini 에서 실제로 밟았다 — 세 provider 가 같은 모양이라 셋 다 붙잡는다).
    client = OpenAI(api_key=secret(settings.openai_api_key))
    raw = list(client.models.list())
    today = date.today().isoformat()
    out: list[ModelInfo] = []
    for m in raw:
        if not _openai_is_chat(m.id):
            continue
        shutdown = getattr(m, "shutdown_date", None)
        # 이미 지난 종료일은 후보가 아니다. 이 필드가 오늘 고친 결함의 조기 경보다.
        if shutdown and str(shutdown) < today:
            continue
        out.append(ModelInfo(id=m.id, shutdown_date=str(shutdown) if shutdown else None))
    return out, len(raw)


def _fetch_gemini(settings: Settings) -> tuple[list[ModelInfo], int]:
    from google import genai

    client = genai.Client(api_key=secret(settings.gemini_api_key))
    raw = list(client.models.list())
    out: list[ModelInfo] = []
    for m in raw:
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" not in actions:
            continue
        out.append(
            ModelInfo(
                id=(m.name or "").removeprefix("models/"),
                display_name=getattr(m, "display_name", None),
                input_token_limit=getattr(m, "input_token_limit", None),
                output_token_limit=getattr(m, "output_token_limit", None),
            )
        )
    return out, len(raw)


def _fetch_anthropic(settings: Settings) -> tuple[list[ModelInfo], int]:
    import anthropic

    client = anthropic.Anthropic(api_key=secret(settings.anthropic_api_key))
    raw = list(client.models.list())
    out = [ModelInfo(id=m.id, display_name=getattr(m, "display_name", None)) for m in raw]
    return out, len(raw)


_FETCHERS: dict[str, Any] = {
    "openai": _fetch_openai,
    "gemini": _fetch_gemini,
    "anthropic": _fetch_anthropic,
}


def _configured_model(settings: Settings, provider: str) -> str | None:
    return getattr(settings, f"{provider}_model", None)


def fetch_provider(
    settings: Settings, provider: str, *, now: float | None = None
) -> ProviderCatalog:
    """한 provider 의 목록. ★실패를 **삼키지 않고 실어 보낸다** — 못 읽은 것과 비어 있는 것은 다르다."""
    now = time.monotonic() if now is None else now
    hit = _cache.get(provider)
    if hit is not None and now - hit[0] < _TTL_SECONDS:
        return hit[1]

    configured = _configured_model(settings, provider)
    if not secret(getattr(settings, f"{provider}_api_key", None)):
        return ProviderCatalog(provider, configured=configured, error="키가 설정되지 않았습니다")

    try:
        models, total = _FETCHERS[provider](settings)
        cat = ProviderCatalog(provider, models=models, total_seen=total, configured=configured)
    except Exception as exc:  # provider 하나가 죽어도 나머지는 살아야 한다
        logger.warning("model catalog failed provider=%s exc_type=%s", provider, type(exc).__name__)
        return ProviderCatalog(provider, configured=configured, error=type(exc).__name__)

    _cache[provider] = (now, cat)
    return cat


def catalog(settings: Settings) -> list[ProviderCatalog]:
    """설정 순서대로 전 provider. ★순서를 보존한다 — 화면의 기본 선택이 그 순서를 따른다."""
    ordered = provider_order(settings)
    rest = [p for p in KNOWN_PROVIDERS if p not in ordered]
    return [fetch_provider(settings, p) for p in [*ordered, *rest]]


def reset_cache() -> None:
    """테스트 전용 — 프로세스 안 TTL 캐시를 비운다."""
    _cache.clear()


class ModelNotAvailableError(ValueError):
    """요청이 고른 provider/model 이 **살아 있는 목록에 없다.**"""


def resolve_override(settings: Settings, *, provider: str | None, model: str | None) -> Settings:
    """요청이 고른 provider/model 을 검증해 **그것만 쓰도록 좁힌** settings 를 만든다.

    ★둘 다 주거나 둘 다 안 주거나다. 모델만 주면 어느 provider 의 것인지 추측해야 하는데,
    추측이 틀리면 사용자는 「왜 다른 모델이 돌았지」를 디버깅하게 된다.
    ★검증은 **살아 있는 목록**으로 한다 — 오타·폐기 모델을 provider 왕복 **전에** 막는다.
      막지 않으면 `gemini-2.0-flash` 처럼 404 가 503 으로 둔갑해 원인이 지워진다.
    ★목록을 못 읽었으면 **통과시킨다** — provider 목록 API 가 죽었다고 해설까지 막을 이유가 없다.
      「못 봤다」로 사용자를 막는 것은 `configured_listed` 가 `None` 인 것과 같은 이유로 틀렸다.
    """
    if provider is None and model is None:
        return settings
    if provider is None or model is None:
        raise ModelNotAvailableError("provider 와 model 은 함께 지정해야 합니다")
    if provider not in KNOWN_PROVIDERS:
        raise ModelNotAvailableError(f"알 수 없는 provider 입니다: {provider}")
    if not secret(getattr(settings, f"{provider}_api_key", None)):
        raise ModelNotAvailableError(f"{provider} 키가 설정되지 않았습니다")

    cat = fetch_provider(settings, provider)
    if cat.error is None and not any(m.id == model for m in cat.models):
        raise ModelNotAvailableError(f"{provider} 의 사용 가능한 모델이 아닙니다: {model}")

    return settings.model_copy(update={"llm_provider_order": provider, f"{provider}_model": model})
