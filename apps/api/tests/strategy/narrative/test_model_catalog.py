"""`narrative/catalog` — provider 에게 **실제 모델 목록을 물어** 설정값과 대조한다.

★왜 생겼나 — 2026-08-28 에 기본값 `gemini-2.0-flash` 가 폐기돼 404 를 내고 있었고
**아무 테스트도 못 잡았다.** 이유는 단순하다: 기존 테스트는 전송을 mock 하므로 모델 id 가
죽었는지 살았는지 **볼 방법이 없다.** 그 사각을 메우는 것이 이 모듈이다.

여기서 잠그는 것 다섯.
 ⑴ 설정한 모델이 목록에 없으면 **False** — 드리프트를 잡는다.
 ⑵ 목록을 **못 읽었으면 `None`**(모른다)이다. `False`(없다)로 접으면 멀쩡한 설정을 오경보한다.
 ⑶ provider 하나가 죽어도 **나머지는 나온다.**
 ⑷ 후보 필터 — Gemini 는 `generateContent` 를 요구하고, OpenAI 는 **지난 종료일**을 뺀다.
 ⑸ TTL 캐시가 같은 창 안에서 **다시 안 부른다**(provider 왕복 3회는 비싸다).
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, SecretStr

from src.strategy.narrative import catalog as C


@pytest.fixture(autouse=True)
def _clear_cache():
    C.reset_cache()
    yield
    C.reset_cache()


class _S(BaseModel):
    """★`SimpleNamespace` 가 아니라 pydantic 모델이다 — `resolve_override` 가 `model_copy` 를 쓴다.
    가짜가 진짜보다 헐거우면 그 차이를 테스트가 못 본다."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm_provider_order: str
    openai_api_key: SecretStr | None
    gemini_api_key: SecretStr | None
    anthropic_api_key: SecretStr | None
    openai_model: str
    gemini_model: str
    anthropic_model: str


def settings(**over: Any) -> Any:
    base = {
        "llm_provider_order": "openai,gemini,anthropic",
        "openai_api_key": SecretStr("sk-x"),
        "gemini_api_key": SecretStr("gk-x"),
        "anthropic_api_key": SecretStr("ak-x"),
        "openai_model": "gpt-4.1-mini",
        "gemini_model": "gemini-3.7-flash",
        "anthropic_model": "claude-sonnet-4-6",
    }
    base.update(over)
    return _S(**base)


def fake_fetchers(monkeypatch, *, openai=None, gemini=None, anthropic=None):
    """provider 별로 (모델목록, 원본수) 또는 예외를 심는다."""

    def mk(spec):
        def _f(_settings):
            if isinstance(spec, Exception):
                raise spec
            return spec

        return _f

    monkeypatch.setitem(C._FETCHERS, "openai", mk(openai if openai is not None else ([], 0)))
    monkeypatch.setitem(C._FETCHERS, "gemini", mk(gemini if gemini is not None else ([], 0)))
    monkeypatch.setitem(
        C._FETCHERS, "anthropic", mk(anthropic if anthropic is not None else ([], 0))
    )


# ── ⑴⑵ configured_listed 의 3값 ────────────────────────────────────────────
def test_configured_model_missing_from_list_is_false(monkeypatch):
    """★이것이 `gemini-2.0-flash` 사건을 잡았을 단언이다."""
    fake_fetchers(monkeypatch, gemini=([C.ModelInfo(id="gemini-3.5-flash-lite")], 1))
    cat = C.fetch_provider(settings(gemini_model="gemini-2.0-flash"), "gemini")
    assert cat.configured_listed is False


def test_configured_model_present_is_true(monkeypatch):
    fake_fetchers(monkeypatch, gemini=([C.ModelInfo(id="gemini-3.5-flash-lite")], 1))
    cat = C.fetch_provider(settings(gemini_model="gemini-3.5-flash-lite"), "gemini")
    assert cat.configured_listed is True


def test_unreadable_list_is_none_not_false(monkeypatch):
    """★「못 봤다」와 「없다」를 같은 값으로 접으면 멀쩡한 설정을 오경보한다."""
    fake_fetchers(monkeypatch, gemini=RuntimeError("boom"))
    cat = C.fetch_provider(settings(), "gemini")
    assert cat.error == "RuntimeError"
    assert cat.configured_listed is None


def test_missing_key_is_none_not_false(monkeypatch):
    fake_fetchers(monkeypatch)
    cat = C.fetch_provider(settings(gemini_api_key=None), "gemini")
    assert cat.configured_listed is None
    assert cat.error is not None


# ── ⑶ 한 provider 의 실패가 나머지를 못 죽인다 ──────────────────────────────
def test_one_provider_failure_does_not_sink_the_others(monkeypatch):
    fake_fetchers(
        monkeypatch,
        openai=([C.ModelInfo(id="gpt-4.1-mini")], 1),
        gemini=RuntimeError("down"),
        anthropic=([C.ModelInfo(id="claude-sonnet-4-6")], 1),
    )
    by = {c.provider: c for c in C.catalog(settings())}
    assert by["openai"].configured_listed is True
    assert by["gemini"].error == "RuntimeError"
    assert by["anthropic"].configured_listed is True


def test_catalog_follows_configured_order_then_the_rest(monkeypatch):
    fake_fetchers(monkeypatch)
    got = [c.provider for c in C.catalog(settings(llm_provider_order="gemini"))]
    assert got[0] == "gemini"
    assert sorted(got) == sorted(C.KNOWN_PROVIDERS)


# ── ⑷ 후보 필터 ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("model_id", "expected"),
    [
        ("gpt-4.1-mini", True),
        ("o3-mini", True),
        ("chatgpt-4o-latest", True),
        # marker 목록이 거르는 것들
        ("gpt-3.5-turbo-instruct", False),
        ("gpt-4o-audio-preview", False),
        ("text-embedding-3-small", False),
        ("whisper-1", False),
        ("dall-e-3", False),
        # ★**접두 검사만이** 거르는 것들. 이 두 줄이 없으면 접두 검사를 죽이는 변이가
        #   초록으로 통과한다(2026-08-28 변이 실측 — 위 음성 예시는 전부 marker 에도 걸린다).
        ("davinci-002", False),
        ("babbage-002", False),
    ],
)
def test_openai_chat_filter(model_id, expected):
    assert C._openai_is_chat(model_id) is expected


def test_openai_drops_models_whose_shutdown_date_has_passed(monkeypatch):
    """★`shutdown_date` 는 오늘 고친 결함의 **조기 경보**다 — 지난 것은 후보가 아니다.

    ★이 테스트는 `_FETCHERS` 를 갈아끼우지 **않는다.** 스텁으로 바꾸면 필터를 테스트가
    재구현하게 되고, 그러면 진짜 `_fetch_openai` 가 죽어도 초록이다. SDK 클래스만 바꾼다.
    """
    past = (date.today() - timedelta(days=1)).isoformat()
    future = (date.today() + timedelta(days=90)).isoformat()
    listed = [
        SimpleNamespace(id="gpt-old", shutdown_date=past),
        SimpleNamespace(id="gpt-new", shutdown_date=future),
        SimpleNamespace(id="gpt-forever", shutdown_date=None),
        SimpleNamespace(id="text-embedding-3-small", shutdown_date=None),
        SimpleNamespace(id="davinci-002", shutdown_date=None),
    ]
    import openai as openai_sdk

    monkeypatch.setattr(
        openai_sdk,
        "OpenAI",
        lambda api_key: SimpleNamespace(models=SimpleNamespace(list=lambda: listed)),
    )
    cat = C.fetch_provider(settings(openai_model="gpt-new"), "openai")
    ids = [m.id for m in cat.models]
    assert "gpt-old" not in ids, "지난 종료일이 후보에 남았다"
    assert "text-embedding-3-small" not in ids, "chat 아닌 모델이 후보에 남았다"
    assert "davinci-002" not in ids, "접두 검사만이 거르는 모델이 후보에 남았다"
    assert {"gpt-new", "gpt-forever"} <= set(ids)
    assert cat.total_seen == 5
    assert next(m for m in cat.models if m.id == "gpt-new").shutdown_date == future


def test_gemini_requires_generate_content(monkeypatch):
    """★후보 필터가 진짜 `_fetch_gemini` 안에서 도는지 잰다 — 스텁으로 우회하지 않는다."""
    listed = [
        SimpleNamespace(
            name="models/gemini-3.5-flash-lite",
            display_name="Gemini 3.5 Flash Lite",
            supported_actions=["generateContent", "countTokens"],
            input_token_limit=1048576,
            output_token_limit=65536,
        ),
        SimpleNamespace(
            name="models/text-embedding-004",
            display_name="Embedding",
            supported_actions=["embedContent"],
            input_token_limit=2048,
            output_token_limit=1,
        ),
    ]
    from google import genai as genai_sdk

    monkeypatch.setattr(
        genai_sdk,
        "Client",
        lambda api_key: SimpleNamespace(models=SimpleNamespace(list=lambda: listed)),
    )
    cat = C.fetch_provider(settings(gemini_model="gemini-3.5-flash-lite"), "gemini")
    assert [m.id for m in cat.models] == ["gemini-3.5-flash-lite"], (
        "generateContent 필터가 안 걸렸다"
    )
    assert cat.total_seen == 2
    got = cat.models[0]
    assert got.display_name == "Gemini 3.5 Flash Lite"
    assert got.input_token_limit == 1048576
    assert cat.configured_listed is True


# ── ⑸ TTL 캐시 ──────────────────────────────────────────────────────────────
def test_second_call_inside_ttl_does_not_refetch(monkeypatch):
    calls = {"n": 0}

    def _f(_s):
        calls["n"] += 1
        return [C.ModelInfo(id="gemini-3.5-flash-lite")], 1

    monkeypatch.setitem(C._FETCHERS, "gemini", _f)
    s = settings()
    C.fetch_provider(s, "gemini", now=1000.0)
    C.fetch_provider(s, "gemini", now=1000.0 + C._TTL_SECONDS - 1)
    assert calls["n"] == 1


def test_call_after_ttl_refetches(monkeypatch):
    """★양성 대조 — 캐시가 **영원히** 물고 있으면 폐기 모델을 영영 못 본다."""
    calls = {"n": 0}

    def _f(_s):
        calls["n"] += 1
        return [C.ModelInfo(id="gemini-3.5-flash-lite")], 1

    monkeypatch.setitem(C._FETCHERS, "gemini", _f)
    s = settings()
    C.fetch_provider(s, "gemini", now=1000.0)
    C.fetch_provider(s, "gemini", now=1000.0 + C._TTL_SECONDS + 1)
    assert calls["n"] == 2


def test_failures_are_not_cached(monkeypatch):
    """실패를 캐시하면 provider 가 살아나도 15분간 죽은 채로 보인다."""
    state = {"fail": True}

    def _f(_s):
        if state["fail"]:
            raise RuntimeError("down")
        return [C.ModelInfo(id="gemini-3.5-flash-lite")], 1

    monkeypatch.setitem(C._FETCHERS, "gemini", _f)
    s = settings()
    assert C.fetch_provider(s, "gemini", now=1000.0).error == "RuntimeError"
    state["fail"] = False
    assert C.fetch_provider(s, "gemini", now=1000.0).configured_listed is False


# ── resolve_override — 요청이 고른 provider/model 을 왕복 **전에** 검증한다 ──────
def test_no_override_returns_settings_untouched(monkeypatch):
    fake_fetchers(monkeypatch)
    s = settings()
    assert C.resolve_override(s, provider=None, model=None) is s


@pytest.mark.parametrize(
    ("provider", "model"),
    [("gemini", None), (None, "gemini-3.5-flash-lite")],
)
def test_provider_and_model_must_come_together(monkeypatch, provider, model):
    """★한쪽만 오면 나머지를 추측해야 하고, 추측이 틀리면 사용자는 조용히 다른 모델을 쓴다."""
    fake_fetchers(monkeypatch)
    with pytest.raises(C.ModelNotAvailableError):
        C.resolve_override(settings(), provider=provider, model=model)


def test_unknown_provider_is_rejected(monkeypatch):
    fake_fetchers(monkeypatch)
    with pytest.raises(C.ModelNotAvailableError):
        C.resolve_override(settings(), provider="llama", model="whatever")


def test_provider_without_key_is_rejected(monkeypatch):
    fake_fetchers(monkeypatch)
    with pytest.raises(C.ModelNotAvailableError):
        C.resolve_override(settings(gemini_api_key=None), provider="gemini", model="x")


def test_model_absent_from_live_list_is_rejected(monkeypatch):
    """★이 검증이 없으면 폐기 모델이 provider 까지 가서 **404 가 503 으로 둔갑**한다."""
    fake_fetchers(monkeypatch, gemini=([C.ModelInfo(id="gemini-3.5-flash-lite")], 1))
    with pytest.raises(C.ModelNotAvailableError):
        C.resolve_override(settings(), provider="gemini", model="gemini-2.0-flash")


def test_valid_override_narrows_order_and_sets_model(monkeypatch):
    fake_fetchers(monkeypatch, gemini=([C.ModelInfo(id="gemini-3.6-flash")], 1))
    out = C.resolve_override(settings(), provider="gemini", model="gemini-3.6-flash")
    assert out.llm_provider_order == "gemini", "고른 provider 만 쓰도록 좁혀야 한다"
    assert out.gemini_model == "gemini-3.6-flash"
    assert out.openai_model == "gpt-4.1-mini", "다른 provider 의 설정은 안 건드린다"


def test_unreadable_list_lets_the_override_through(monkeypatch):
    """★목록 API 가 죽었다고 해설까지 막지 않는다 — `configured_listed is None` 과 같은 이유다."""
    fake_fetchers(monkeypatch, gemini=RuntimeError("list api down"))
    out = C.resolve_override(settings(), provider="gemini", model="gemini-3.6-flash")
    assert out.gemini_model == "gemini-3.6-flash"


# ── HTTP 계약 ───────────────────────────────────────────────────────────────
# ★왜 이 절이 있나 — 위의 단위 테스트 29건이 전부 초록인 채로 엔드포인트가 **모든 요청에 500**
#   을 냈다. `@limiter.limit` 는 헤더를 넣을 `response: Response` 를 시그니처에서 찾는데 그것이
#   없었고(slowapi `_inject_headers`), `catalog()` 만 재는 테스트는 그 층을 지나지 않는다.
#   ⇒ **라우터가 얇다는 것은 안 재도 된다는 뜻이 아니다.**
def _client(monkeypatch):
    from fastapi.testclient import TestClient

    from src.auth.dependencies import get_current_user
    from src.auth.schemas import CurrentUser
    from src.main import create_app
    from src.strategy.narrative import router as router_mod

    fake_fetchers(
        monkeypatch,
        openai=([C.ModelInfo(id="gpt-4.1-mini")], 1),
        gemini=([C.ModelInfo(id="gemini-3.5-flash-lite", display_name="Flash Lite")], 1),
        anthropic=RuntimeError("provider down"),
    )
    # ★라우터가 보는 settings 를 고정한다. 안 하면 **주변 환경이 결과를 정한다** — 로컬에는
    #   `.env.local` 의 키가 있어 fetcher 가 돌고, CI 에는 키가 없어 `fetch_provider` 가
    #   그 앞의 키 검사에서 끊긴다. 그래서 로컬 초록 / CI 빨강이었다(2026-08-28 실측).
    monkeypatch.setattr(router_mod, "settings", settings(), raising=True)
    app = create_app()
    return app, TestClient(app), get_current_user, CurrentUser


def test_models_endpoint_requires_auth(monkeypatch):
    _app, client, _dep, _cu = _client(monkeypatch)
    assert client.get("/api/v1/llm/models").status_code == 401


def test_models_endpoint_returns_200_and_the_documented_shape(monkeypatch):
    """★이 단언이 `response: Response` 누락(전건 500)을 잡는다."""
    from uuid import uuid4

    app, client, dep, CurrentUserCls = _client(monkeypatch)
    app.dependency_overrides[dep] = lambda: CurrentUserCls(id=uuid4(), auth_subject="t")
    try:
        r = client.get("/api/v1/llm/models")
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body) == {"providers", "order", "active"}
        by = {p["provider"]: p for p in body["providers"]}
        assert set(by) == set(C.KNOWN_PROVIDERS), "provider 하나가 죽어도 전부 실려야 한다"
        # provider 가 죽은 것과 키가 없는 것은 **다른 사유**지만 둘 다 error 로 실린다.
        # 여기서는 fetcher 예외 경로를 고정했으므로 그 이름이 나와야 한다.
        assert by["anthropic"]["error"] == "RuntimeError"
        assert by["anthropic"]["configured_listed"] is None
        assert by["gemini"]["models"][0]["display_name"] == "Flash Lite"
        # provider 가 안 준 필드는 **없는 게 아니라 null** 이다(`_KIT.md` §4.9 — 화면이 자리를 비운다).
        assert by["openai"]["models"][0]["display_name"] is None
    finally:
        app.dependency_overrides.clear()
