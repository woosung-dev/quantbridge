# `audit/` — 보안 감사 리포트 archive

> **용도:** CSO/Security review / pen-test / compliance audit 산출물 보관소
> **상위 docs 표준 분류표:** [`../README.md`](../README.md)

## 현재 보유 (1 파일)

| 파일                                                                           | 일자       | 주제                                            | 결과             |
| ------------------------------------------------------------------------------ | ---------- | ----------------------------------------------- | ---------------- |
| [`2026-04-16-trading-demo-security.md`](./2026-04-16-trading-demo-security.md) | 2026-04-16 | Sprint 6 Trading Demo (Bybit testnet) 보안 감사 | (파일 내부 참조) |

## 향후 추가 패턴

신규 보안 감사 추가 시 다음 명명 규칙:

```
audit/YYYY-MM-DD-<주제>.md
```

예시 후보:

- `audit/2026-XX-XX-trading-mainnet-pre-launch.md` — Beta 오픈 전 mainnet 보안 검증
- `audit/2026-XX-XX-aes256-key-rotation.md` — 거래소 API key 회전 검증
- `audit/2026-XX-XX-clerk-jwt-boundary.md` — JWT 검증 경계 audit

## CSO mode 운영

`/cso` 슬래시 (gstack skill — daily / comprehensive 두 모드) 실행 시 본 디렉토리에 저장. 자세한 내용:

- **daily mode** — 8/10 confidence gate, zero-noise 일일 점검
- **comprehensive mode** — 2/10 bar, 월간 deep scan (OWASP Top 10 + STRIDE + supply chain)

## 활용 정책

- 기존 audit 파일은 **삭제 금지** (역사적 맥락 + 트렌드 추적용)
- 결과 요약은 [`../REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) 의 P0/P1 BL 등록과 cross-link
- 중대한 발견은 [`../dev-log/`](../dev-log/) 에 ADR 로 별도 기록
