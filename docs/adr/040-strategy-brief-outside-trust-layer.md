# ADR-040 — 전략 브리핑은 Trust Layer **밖**의 보조 설명이다

- **상태:** Accepted (2026-08-27)
- **범위:** `apps/api/src/strategy/brief/` · `apps/web/src/features/strategy/components/brief/`
- **관련:** [ADR-011](./011-pine-execution-strategy-v4.md)(§6 투명성 UX) · [ADR-020](./020-trust-layer-ci-design.md)(§3 F행) · [ADR-003](./003-pine-runtime-safety-and-parser-scope.md)(부분 실행 금지) · [ADR-042](./042-pine-to-python-readonly-renderer.md)

## 결정

1. 백테스트 **제출 전에** 「이 전략이 무엇을 하는가」를 보여주는 **전략 브리핑** 화면을 만든다.
2. 브리핑은 **2층**이고 층의 권한이 다르다.
   - **결정론 층** — `analyze_coverage` · `extract_content` · `classify_script` · `SignalExtractor`
     가 AST 에서 뽑은 사실. **판정어(실행 가능 / 미지원 / degraded / Track)는 전부 이 층이 낸다.**
   - **해설 층** — LLM 산문. **판정을 하지 않는다.** 시각적으로 분리하고 「AI 해설 — 판정이 아닙니다」를 붙인다.
3. **LLM 문장은 근거 없이 렌더하지 않는다.** 출력 계약이 항목마다 `pine_lines: int[]` 를
   요구하고, 빈 배열이면 그 항목을 그리지 않는다.
4. **LLM 실패는 화면을 죽이지 않는다.** 엔드포인트를 둘로 나눠(`/brief` · `/brief/narrative`)
   결정론 층이 먼저 완결되고 해설만 뒤에 채워진다.

## 이유

「결과와 가정이 얼마나 정직하게 보이는가」가 이 제품의 유일한 자산인데([PRD](../PRD.md) §1),
지금은 등록 직후 바로 백테스트로 간다. 사용자가 **무엇을 돌리는지 모른 채 숫자를 받는다.**

이 축은 새 발명이 아니다 — [ADR-011](./011-pine-execution-strategy-v4.md) §6 이 긍정적 결과로
「**투명성 UX — 사용자에게 「이 스크립트는 이렇게 해석됐습니다」**」를 이미 적었고,
[ADR-017](./017-fe-polish-bundle-1-2-retro.md) 이 `ParseDialog`/`TabParse` 로 한 번 구현했다.
그 컴포넌트는 지금 없고 역할만 `DiagnosticsStrip`/`ParseResultPanel` 로 흩어져 있다.

재료도 이미 있다 — `pine_v2/ast_extractor.py` 가 선언·파라미터 전량·주문 호출을 `to_dict()` 까지
뽑고, `pine_v2/coverage.py` 가 미지원 호출을 **줄번호와 함께** 낸다. 없는 것은 **노출과 화면**뿐이다.

## ADR-020 §3 F행과의 경계 — 이것이 이 ADR 의 본체다

[ADR-020](./020-trust-layer-ci-design.md) §3 은 「**F. LLM 기반 결과 해석/비교 ❌ — Trust Layer 가
LLM 노이즈 섞이면 신뢰도 역행**」이라고 적었다. 그 표는 **Trust Layer CI 의 비교 오라클**을 고르는
표다. 거기서 기각한 것은 **회귀를 판정하는 자리에 LLM 을 앉히는 것**이고, 채택된 것은
골든 + Mutation Oracle(D+E)이다.

| | ADR-020 F (기각) | ADR-040 해설 층 (채택) |
| --- | --- | --- |
| 누가 읽나 | CI | 사람 |
| 무엇을 하나 | **판정** (regression 여부) | **설명** |
| 틀리면 | 회귀가 통과한다 | 사용자가 한 문단을 오해한다 |
| 되돌릴 수 있나 | 아니오 (머지됨) | 예 (옆에 결정론 층이 있다) |

⇒ **판정은 결정론 층이 독점한다.** 해설 층이 「이 전략은 실행 가능합니다」를 말하는 일은
설계상 불가능해야 하고, 그것을 위 결정 2·3 이 집행한다.

## 트레이드오프

- **LLM 이 틀린 설명을 할 수 있다.** 근거 줄 요구가 환각을 줄이지만 없애지 못한다.
  대가로 얻는 것은 「모르고 돌리는 것」의 제거다. 근거 줄이 있으므로 **사용자가 대조할 수 있다** —
  이것이 Trust Layer 밖에 두면서도 정직할 수 있는 유일한 이유다.
- **LLM 비용·지연이 붙는다.** `StrategyVersion.source_hash` 로 캐시해 같은 코드 = 같은 브리핑이다.
- **화면이 하나 늘어난다.** 새 라우트를 만들지 않고 기존 표면 2곳(편집 화면 진단 탭 · 백테스트 폼)에
  같은 컴포넌트를 얹어 상쇄한다.
