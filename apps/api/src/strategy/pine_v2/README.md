# pine_v2 — Tier-0 pynescript 포크 기반 Pine 파이프라인

> Sprint 8a (ADR-011 Phase 1). H1 MVP scope: TP/SL/LONG/SHORT만.

## 라이선스 경계 (엄수)

- **pynescript:** LGPL-3.0. `backend/pyproject.toml`에 버전 pin된 PyPI 의존성으로만 사용.
- **절대 금지:**
  - 이 디렉토리에 pynescript 소스 복사
  - pynescript 내부 구현을 QB 코드로 재작성 (공개 API만 호출)
  - LGPL 파일을 다른 모듈로 이동
- **허용:** `parser_adapter.py` / `ast_metrics.py`에서 `import pynescript` + 공개 API 호출
- 혹시 향후 포크·패치가 필요하면 `third_party/pynescript/` 서브디렉토리에 원본 LGPL 헤더 보존 + 리포 루트 `NOTICE` 갱신 후 격리
- PyneCore `transformers/` (Apache 2.0)는 **Sprint 8a Week 2+에 별도로 참조 이식**. Day 1 범위 밖.

## 기존 `pine/` 모듈과의 관계

- `backend/src/strategy/pine/`는 Sprint 7b까지 건드리지 않음 (dogfood 복구 경로)
- `pine_v2/`가 Tier-0 (파서) → Tier-3 (strategy 네이티브)까지 완성되면 `pine/`에서 교체
- 교체 시점: Sprint 8c 종료 예정

## Day 1 (이 커밋) 범위

- 패키지 스캐폴드 + LGPL 격리 정책 명문
- `parse_and_run_v2()` compat 스텁 (NotImplementedError)
- pynescript 0.3.0 baseline 회귀 테스트 (Phase -1 E2 수치와 동일성 검증)

## Sprint 8a 남은 Day

- Day 2~Week 1: PyneCore `transformers/` 참조 이식 (persistent/series/security/nabool)
- Week 2~3: Bar-by-bar 이벤트 루프 + 렌더링 객체 범위 A 런타임
