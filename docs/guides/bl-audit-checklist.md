# BL Audit Checklist (Sprint Kickoff 의무)

> **목적:** Sprint 시작 시 active BL trigger 도래 항목을 자동 식별 + sprint scope 결정에 반영.
> **도입:** Sprint 28 Slice 1a (Phase C.2 prototype).
> **승격 경로:** Sprint 29+ kickoff 시 동일 checklist 사용 시 영구 규칙 승격 (`.ai/project/lessons.md`).

## 사용법

Sprint kickoff 시 (sprint-kickoff-template.md 첫 작업) 본 checklist 1회 실행:

1. **자동 추출** — `grep` script 로 active BL 목록 + status 추출
2. **수동 review** — P0/P1 trigger 도래 여부 (sprint scope 적합도)
3. **결과 반영** — sprint plan / dev-log frontmatter 의 "Recent BLs" + "신규 BL count" 갱신

## Checklist

### A. Active BL 자동 추출

```bash
scripts/bl-audit.sh                 # 판정 + P별 내역 + 3면 불일치 + UNKNOWN 목록
scripts/bl-audit.sh --list ACTIVE   # id / 우선순위 / 줄번호 만
```

기대 결과: **P0 버킷은 스크립트가 항상 전량 펼친다** — 여기서 진행 중 P0 를 본다.
2026-07-31 실측 기준 P0 ACTIVE = **BL-003** 1건(Bybit mainnet runbook). Sprint 28 진입 시점의
BL-001/002/004 는 Resolved 라 `_archived.md` 로 내려갔다.

> ★**낡은 방법(`grep … | head -20`)은 쓰지 마라.** 섹션이 217개인데 20개만 보여줘 조용히
> 잘렸고, `grep -B1 "P0"` 는 우선순위 줄을 못 집는다. 더 나쁜 것은 그 다음 세대 산식(인라인
> awk)이 **본문에 `Resolved` 문자열이 있으면 RESOLVED** 로 봐서 **cross-ref 한 줄이 항목을
> 지웠다**는 것이다 — BL-003(P0, 열려 있음)이 자기 섹션의 `BL-004 ✅ Resolved` 때문에
> RESOLVED 로 집계돼 **P0 active 를 0 으로 보고했다.** 지금 산식의 SSOT 는 섹션의
> `**상태:**` / `**Status:**` 줄이고, 근거가 없으면 **UNKNOWN 으로 남긴다**(추측 금지).

### B. Trigger 도래 여부 review

| BL ID  | 우선도 | Trigger                                          | Sprint N 적합도           |
| ------ | ------ | ------------------------------------------------ | ------------------------- |
| BL-XXX | P0     | 명시 trigger (예: "Bybit Demo 1주 안정 운영 후") | ✅ trigger 도래 / ⏳ 대기 |
| BL-XXX | P1     | 명시 trigger                                     | ✅ / ⏳                   |

### C. Beta BL 진행 상황 (BL-070~075)

```bash
grep -A3 "BL-07" docs/backlog.md | head -20
```

기대 결과: 도메인 + DNS / Backend production / Resend / 캠페인 / 인터뷰 / H2 게이트 6 항목 status.

### D. sprint scope 결정

- Trigger 도래 BL 중 우선도 ≥ P1 항목 = sprint scope 후보
- Type B (risk-critical) sprint 인 경우 P0 우선
- Type A (신규 기능) sprint 인 경우 도메인 progress 매트릭스 참조

### E. Dual metric 입력값 준비 (sprint 종료 시 사용)

- sprint 진입 시점 P0 잔여 카운트 기록 (dev-log frontmatter "기존 P0 잔여" 의 진입 값)
- sprint 안 새로 발견될 BL 카운트 추적 (Slice 별 / Stage 별)

## 영구 규칙 후보 (Sprint 28 정착 시 승격)

각 sprint kickoff 시:

- [ ] BL audit checklist 1회 실행
- [ ] 결과 sprint-template.md frontmatter 의 "Recent BLs" + "기존 P0 잔여 (진입 시점)" 채움
- [ ] sprint 종료 시 dual metric 측정 시 본 진입 값과 비교

## 자동화 현황

- ✅ `.claude/settings.json` SessionStart hook 으로 본 checklist 자동 표시
- ✅ **script 화 = [`scripts/bl-audit.sh`](../../scripts/bl-audit.sh) (2026-07-31 신설).** 판정 SSOT =
  섹션의 `**상태:**` / `**Status:**` 줄. 인덱스 표 ✅/🟡 · `docs/roadmap.md` 체크박스와 3면 대조하고,
  **불일치 또는 UNKNOWN 이 있으면 exit 1** 이라 게이트에 물릴 수 있다.
- ⏳ GitHub Actions — PR 마다 자동 검증. 스크립트는 준비됐으나 이 레포 CI 는 러너 미할당이라 미배선
  (`scripts/final-gates.sh` 와 같은 사정).
