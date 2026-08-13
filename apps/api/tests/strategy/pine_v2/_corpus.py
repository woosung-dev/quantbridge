"""Trust Layer 코퍼스 목록 SSOT ([BL-588], 2026-08-03).

이 목록은 **세 곳에 따로 적혀 있었다** — `test_trust_layer_parity.py`(7벌) ·
`regen_trust_layer_baseline.py`(7벌) · `test_mutation_oracle.py`(**5벌**). 앞 둘은 "동명
상수와 쌍이다" 라는 주석으로 서로를 가리켰지만 셋째는 아무도 가리키지 않았고, 그래서
2026-08-03 `backtest-metric-oracle` 이 위험조정지표 채널을 열려고 추가한 비축퇴 2벌
(`s4_hma_curvature` / `s5_ema_trend`)이 **mutation oracle 에는 확산되지 않았다.**

그 2벌이 없으면 mutation oracle 은 앞 5벌만 도는데, 그 5벌은 사이징 미선언으로 자본이
음수로 끝나 sharpe 가 전부 `0.00000000` 이고 sortino·calmar 가 전부 null 이다 — **세 지표의
산술이 회귀해도 값이 움직일 여지가 없다.** 감지 못 하는 변이가 구조적으로 존재했다는 뜻이다.

주석으로 "쌍이다" 를 적는 대신 **하나만 두고 셋이 import** 한다.
"""

from __future__ import annotations

# P-3 실행 대상. 앞 5벌 = Path β 원본, 뒤 2벌 = 비축퇴 코퍼스(위험조정지표 값 채널).
RUNNABLE_CORPUS: tuple[str, ...] = (
    "s1_pbr",
    "s2_utbot",
    "s3_rsid",
    "i1_utbot",
    "i2_luxalgo",
    # ★위 5벌은 사이징 미선언으로 자본이 음수로 끝나 sharpe 가 5벌 모두 "0.00000000",
    #   sortino·calmar 가 5벌 모두 null 이다. 아래 2벌이 그 채널을 연다.
    "s4_hma_curvature",  # 3지표 전부 음수 (sharpe -2.30) — 부호 오류 감지용 짝
    "s5_ema_trend",  # 3지표 전부 양수 (sharpe +0.36)
)

# Sprint Y1 Coverage Analyzer 가 `is_runnable=false` 로 reject.
# 실행하지는 않지만 **정답지에는 기록이 남아야** 한다(`{"note": "Skipped ..."}`).
SKIPPED_CORPUS: tuple[str, ...] = ("i3_drfx",)

# 정답지 `corpora` 키 집합의 정본. `test_envelope_corpus_set_is_exactly_the_canonical_list`
# 가 이것과 `baseline_metrics.json` 을 대조한다.
ALL_CORPUS: tuple[str, ...] = RUNNABLE_CORPUS + SKIPPED_CORPUS
