# Sprint 58 Close-out — BL-241 + BL-242 + BL-243 Pine Coverage 확장

> **Date:** 2026-05-11
> **PR:** #264 main @`aa435a7` (squash merge)
> **Active BL 변화:** 92 → 89 (BL-241/242/243 Resolved, -3 net)

---

## 1. 완료 요약

dogfood에서 발견된 Pine Script 호환성 문제 3종 해결.

| BL     | 내용                                       | status          |
| ------ | ------------------------------------------ | --------------- |
| BL-241 | ta.wma/hma/bb/cross/mom/obv + fixnan (7종) | **✅ Resolved** |
| BL-242 | strategy.equity + display 함수 ignore      | **✅ Resolved** |
| BL-243 | 거래 목록 UTC 타임존 라벨                  | **✅ Resolved** |

---

## 2. 기술 결정 기록

### 2.1 float length 버그

Pine Script에서 `tclength/2` (division) 결과가 float으로 전달됨. `deque(maxlen=300.0)` → `TypeError`. 각 함수에 `length = int(length)` 추가로 해결. 기존 함수(`ta_sma` 등)는 `deque(maxlen=length)` 사용하나 테스트에서 정수만 전달되어 발견 안 됨.

### 2.2 ta.obv attribute 처리

Pine v5에서 `ta.obv`는 function call이 아닌 series attribute (`ta.obv`, `ta.obv[1]` 등). `interpreter._eval_attribute()`에서 `self.stdlib.call("ta.obv", id(node), [close, vol, prev_close])` 로 라우팅. `_names.py` TA_FUNCTIONS에 포함시켜 coverage analyzer에서 지원으로 인식.

### 2.3 ta.dmi 이연

DrFX에서 `[_, _, tvr] = ta.dmi(14, 14)` 사용 확인. DMI+ADX 계산은 `ta.rma` 기반 3-pass 계산으로 복잡. dashboard 표시용이므로 signal에 무관. Sprint 59+ 이연 (BL 유지).

### 2.4 fixnan → ta.alma 테스트 교체

`fixnan`이 BL-241로 supported됨에 따라 3개 테스트 파일의 "unsupported 함수 가정" 테스트를 `ta.alma`로 교체:

- `test_sprint29_slice_b.py`
- `test_walk_forward_unsupported_pine.py` ← CI 실패로 발견, hotfix push
- `test_coverage_sprint21.py`

---

## 3. 검증 evidence

```
BE pine_v2:    507 passed (baseline 498 → +9 신규, 0 fail)
FE vitest:     680 passed (0 fail)
SSOT 4 inv:    13 passed
BE ruff:       all checks passed
BE mypy:       no errors
FE tsc:        0 errors
DrFX unsupported attrs: 14 → 0
DrFX unsupported funcs: 18 → 14 (array.*/MTF/alma/dmi 만 남음)
```

CI hotfix: `test_walk_forward_unsupported_pine.py` fixnan→ta.alma 교체 (PR #264 후 push).

---

## 4. 커밋 히스토리

```
8182556 fix(test): fixnan→ta.alma (CI hotfix)
21b48c5 chore(pine): Sprint 58 close-out — float length 버그 fix + ruff/mypy clean + docs
6e34aee feat(pine): BL-242b display 함수 ignore
f02662b feat(pine): BL-242a strategy.equity
197a3f7 feat(pine): BL-241 ta.wma/cross/mom/fixnan + ta.hma/bb/obv
b9d6b4b feat(backtest): BL-243 FE UTC 라벨
```

---

## 5. Sprint 59 다음 분기

Day 7 인터뷰 (2026-05-16) 결과 따라:

- NPS ≥7 + bug 0 + 본인 의지 → Beta 본격 (BL-070~075)
- Pine 계속 → ta.dmi / BL-235 N-dim viz / BL-236 objective 자유화
- mainnet → BL-003/BL-005
