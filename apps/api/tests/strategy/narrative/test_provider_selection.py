"""`providers.complete_json` — **어느 provider 를 쓸지는 설정이 정한다**.

★왜 이 파일이 생겼나 — 종전에는 「anthropic 우선 → gemini fallback」이 `narrative/service.py` 와
`generate_service.py` **양쪽에 복제**돼 있었다. 환경마다 가진 키가 달라서(2026-08-28 실측:
로컬 openai 200 · gemini 400 · anthropic 401 · 서버는 셋 다 비어 있음) 순서를 설정으로 뺐다.

여기서 잠그는 것 넷.
 ⑴ 순서를 **설정이** 정한다. 하나만 적으면 그 provider 만 쓴다.
 ⑵ **키 없는 provider 는 건너뛴다** — 설정에 적혀 있어도 시도조차 안 한다.
 ⑶ 세 provider 가 **전부 스키마를 강제**한다(빠지면 조용히 「프롬프트로 부탁하기」로 후퇴).
 ⑷ [BL-772] — provider 예외 문자열이 호출자에게 **안 샌다**.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from src.strategy.narrative import providers as P

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"summary": {"type": "string"}, "n": {"type": "integer"}},
    "required": ["summary", "n"],
}
PAYLOAD = {"summary": "ok", "n": 1}


def settings(order: str, **keys: str | None) -> Any:
    return SimpleNamespace(
        llm_provider_order=order,
        anthropic_api_key=SecretStr(keys["anthropic"]) if keys.get("anthropic") else None,
        openai_api_key=SecretStr(keys["openai"]) if keys.get("openai") else None,
        gemini_api_key=SecretStr(keys["gemini"]) if keys.get("gemini") else None,
        anthropic_model="claude-sonnet-4-6",
        openai_model="gpt-4.1-mini",
        gemini_model="gemini-2.0-flash",
    )


# ── 스텁 ─────────────────────────────────────────────────────────────────────
def stub_anthropic(monkeypatch, captured: dict, *, fail: str | None = None, tool: bool = True):
    class _M:
        def create(self, **kw):
            captured.update(kw)
            if fail:
                raise RuntimeError(fail)
            block = (
                SimpleNamespace(type="tool_use", name=kw["tools"][0]["name"], input=PAYLOAD)
                if tool
                else SimpleNamespace(type="text", text="설명드리자면...")
            )
            return SimpleNamespace(content=[block])

    monkeypatch.setattr(P.anthropic, "Anthropic", lambda api_key: SimpleNamespace(messages=_M()))


def stub_openai(monkeypatch, captured: dict, *, fail: str | None = None, finish: str = "stop"):
    class _C:
        def create(self, **kw):
            captured.update(kw)
            if fail:
                raise RuntimeError(fail)
            msg = SimpleNamespace(content=json.dumps(PAYLOAD))
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish)])

    monkeypatch.setattr(
        P, "OpenAI", lambda api_key: SimpleNamespace(chat=SimpleNamespace(completions=_C()))
    )


def stub_gemini(monkeypatch, captured: dict, *, fail: str | None = None):
    class _M:
        def generate_content(self, **kw):
            captured.update(kw)
            if fail:
                raise RuntimeError(fail)
            return SimpleNamespace(text=json.dumps(PAYLOAD))

    monkeypatch.setattr(P.genai, "Client", lambda api_key: SimpleNamespace(models=_M()))


def call(st) -> tuple[dict, str]:
    return P.complete_json(st, system="s", user="u", schema=SCHEMA, tool_name="t")


# ── ⑴ 순서를 설정이 정한다 ───────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ("openai", "openai"),
        ("gemini", "gemini"),
        ("anthropic", "anthropic"),
        ("gemini,openai", "gemini"),
        ("openai,anthropic", "openai"),
    ],
)
def test_configured_order_decides_which_provider_answers(monkeypatch, order, expected):
    cap: dict[str, Any] = {}
    stub_anthropic(monkeypatch, cap)
    stub_openai(monkeypatch, cap)
    stub_gemini(monkeypatch, cap)
    _, provider = call(settings(order, anthropic="k", openai="k", gemini="k"))
    assert provider == expected


def test_single_entry_means_no_fallback(monkeypatch):
    """★하나만 적으면 그것만 쓴다 — 실패해도 다른 provider 로 안 넘어간다."""
    cap: dict[str, Any] = {}
    stub_openai(monkeypatch, cap, fail="boom")
    stub_anthropic(monkeypatch, cap)  # 살아 있지만 순서에 없다
    with pytest.raises(RuntimeError):
        call(settings("openai", openai="k", anthropic="k"))


def test_unknown_names_are_ignored_not_fatal(monkeypatch):
    """오타가 전체를 막으면 안 된다."""
    cap: dict[str, Any] = {}
    stub_openai(monkeypatch, cap)
    assert P.provider_order(settings("opnai,openai")) == ["openai"]
    _, provider = call(settings("opnai,openai", openai="k"))
    assert provider == "openai"


# ── ⑵ 키 없는 provider 는 건너뛴다 ───────────────────────────────────────────
def test_provider_without_key_is_skipped_entirely(monkeypatch):
    """★설정에 적혀 있어도 **시도조차 안 한다**. 시도하면 무의미한 401 지연이 붙는다."""
    cap: dict[str, Any] = {}
    tried: list[str] = []
    monkeypatch.setattr(P.anthropic, "Anthropic", lambda api_key: tried.append("anthropic"))
    stub_openai(monkeypatch, cap)

    st = settings("anthropic,openai", openai="k")  # anthropic 키 없음
    assert P.available_providers(st) == ["openai"]
    _, provider = call(st)
    assert provider == "openai"
    assert tried == [], "키 없는 provider 를 시도했다"


def test_no_key_anywhere_names_what_to_set():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        call(settings("anthropic,openai,gemini"))


# ── ⑶ 세 provider 전부 스키마를 강제한다 ─────────────────────────────────────
def test_anthropic_pins_tool_choice(monkeypatch):
    cap: dict[str, Any] = {}
    stub_anthropic(monkeypatch, cap)
    call(settings("anthropic", anthropic="k"))
    assert cap["tool_choice"] == {"type": "tool", "name": "t"}
    assert cap["tools"][0]["input_schema"]["required"] == ["summary", "n"]


def test_openai_uses_structured_outputs_strict(monkeypatch):
    cap: dict[str, Any] = {}
    stub_openai(monkeypatch, cap)
    call(settings("openai", openai="k"))
    rf = cap["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    # ★strict 는 모든 object 에 additionalProperties:false 와 전체 required 를 요구한다.
    assert rf["json_schema"]["schema"]["additionalProperties"] is False


def test_gemini_uses_response_schema(monkeypatch):
    cap: dict[str, Any] = {}
    stub_gemini(monkeypatch, cap)
    call(settings("gemini", gemini="k"))
    assert cap["config"].response_mime_type == "application/json"
    assert cap["config"].response_schema is not None


def test_strict_helper_fills_nested_objects():
    """중첩 object/array 까지 채워야 한다 — 하나라도 빠지면 OpenAI 가 400 을 준다."""
    nested = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"type": "object", "properties": {"a": {"type": "string"}}},
            }
        },
    }
    out = P._strict(nested)
    assert out["additionalProperties"] is False
    assert out["properties"]["items"]["items"]["additionalProperties"] is False
    assert out["properties"]["items"]["items"]["required"] == ["a"]
    # 원본을 훼손하지 않는다 — 같은 스키마를 다른 provider 도 쓴다.
    assert "additionalProperties" not in nested


# ── ⑷ [BL-772] 예외 문자열 미반사 ────────────────────────────────────────────
def test_provider_exception_strings_do_not_reach_the_caller(monkeypatch):
    leak = "https://api.openai.com/v1/chat request_id=req_LEAK sk-proj-SECRET"
    cap: dict[str, Any] = {}
    stub_openai(monkeypatch, cap, fail=leak)
    stub_gemini(monkeypatch, cap, fail=leak)

    with pytest.raises(RuntimeError) as ei:
        call(settings("openai,gemini", openai="k", gemini="k"))
    msg = str(ei.value)
    for frag in ("api.openai.com", "request_id", "req_LEAK", "sk-proj"):
        assert frag not in msg, f"{frag} 가 샜다"


def test_fallback_moves_on_after_failure(monkeypatch):
    """앞이 죽으면 뒤로 넘어간다 (양성 대조 — 위 단언이 「항상 실패해서」가 아님을 증명)."""
    cap: dict[str, Any] = {}
    stub_openai(monkeypatch, cap, fail="boom")
    stub_gemini(monkeypatch, cap)
    _, provider = call(settings("openai,gemini", openai="k", gemini="k"))
    assert provider == "gemini"


def test_truncated_openai_response_is_a_failure_not_partial_json(monkeypatch):
    """★길이 상한에서 잘린 응답을 성공으로 내면 화면이 반쪽 해설을 진짜로 그린다."""
    cap: dict[str, Any] = {}
    stub_openai(monkeypatch, cap, finish="length")
    with pytest.raises(RuntimeError):
        call(settings("openai", openai="k"))


def test_anthropic_without_tool_block_is_a_failure(monkeypatch):
    cap: dict[str, Any] = {}
    stub_anthropic(monkeypatch, cap, tool=False)
    with pytest.raises(RuntimeError):
        call(settings("anthropic", anthropic="k"))
