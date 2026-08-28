"""[ADR-040] 해설 층 스키마.

★**이 층은 판정하지 않는다.** 실행 가능/미지원/degraded/Track 은 전부 결정론 층(`/brief`)이 낸다.
여기 있는 것은 산문이고, 화면은 이것을 **「AI 해설 — 판정이 아닙니다」로 격리해** 그린다.

★**근거 없는 문장은 존재하지 않는다.** 모든 항목이 `pine_lines` 를 요구하고, 서버가 **실재하지 않는
줄을 가리키는 항목을 버린다**(`service._ground`). 클라이언트 판단에 맡기지 않는 이유는 하나 —
버리는 규칙이 두 곳에 있으면 언젠가 한쪽만 고쳐진다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 전략 유형. LLM 이 자유 문자열을 내면 화면이 무한한 라벨을 다뤄야 하므로 닫힌 집합으로 강제한다.
NarrativeStyle = Literal[
    "trend_following",
    "mean_reversion",
    "breakout",
    "volatility",
    "other",
]


class NarrativeNote(BaseModel):
    """해설 한 줄 + **소스 근거**."""

    text: str
    # ★비면 렌더하지 않는다. 근거를 못 대는 문장은 이 제품에서 값이 음수다.
    pine_lines: list[int] = Field(default_factory=list)


class StrategyNarrativeResponse(BaseModel):
    """`GET /strategies/{id}/brief/narrative` 응답.

    `/brief` 와 **같은 `source_hash`** 를 실어 화면이 두 응답이 같은 소스를 말하는지 대조할 수 있게 한다.
    """

    source_hash: str
    provider: Literal["anthropic", "openai", "gemini"]
    summary: str
    style: NarrativeStyle
    assumptions: list[NarrativeNote] = Field(default_factory=list)
    risks: list[NarrativeNote] = Field(default_factory=list)
    # 근거가 실재하지 않아 버려진 항목 수. >0 이면 LLM 이 없는 줄을 지어냈다는 뜻이라 관측 가치가 있다.
    dropped_ungrounded: int = 0


# ── [ADR-041] 자연어 → 전략 생성 ────────────────────────────────────────────
class GenerateStrategyRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=2000)
    symbol: str = Field(default="BTC/USDT", max_length=32)
    timeframe: str = Field(default="1h", max_length=16)


class DriftReport(BaseModel):
    """★LLM 이 낸 Python 과 **실제 실행되는 Pine** 이 같은 전략인지.

    ★★**이 보고서는 위험을 제거하지 않는다. 가시화한다.** 통과한 Pine 을 [ADR-042] 렌더러로
    Python 화해 LLM 이 쓴 Python 과 대조하는 방식이라, **의미가 같은데 표현이 다른 경우와
    표현이 같은데 의미가 다른 경우를 완전히 가르지 못한다**([ADR-041] §트레이드오프).
    그래서 화면은 「다릅니다」가 아니라 「**다를 수 있습니다**」로 말해야 한다.
    """

    # 렌더러가 Pine 에서 뽑은 정본 Python. 어긋나면 이쪽이 진실이다.
    rendered_python: str
    # 두 산출물이 함께 쓰는 식별자 수 대비 LLM 쪽에만 있는 것들.
    only_in_llm: list[str] = Field(default_factory=list)
    only_in_rendered: list[str] = Field(default_factory=list)

    @property
    def diverged(self) -> bool:
        return bool(self.only_in_llm or self.only_in_rendered)


class GenerateStrategyResponse(BaseModel):
    """생성 결과. **Pine 이 정본**이고 Python 은 사람이 읽는 뷰다."""

    provider: Literal["anthropic", "openai", "gemini"]
    pine_source: str
    llm_python: str
    notes: list[str] = Field(default_factory=list)
    # `analyze_coverage` all-or-nothing 판정. False 면 저장하지 않는다.
    is_runnable: bool
    unsupported: list[str] = Field(default_factory=list)
    # 실행 가능할 때만 채워진다 — 못 도는 Pine 은 렌더 기준선이 될 수 없다.
    drift: DriftReport | None = None
