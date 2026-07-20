<!-- 17벌 프로토타입이 실제로 인쇄한 값만으로 확정한 용어·칩 톤·CSS 이름 SSOT (React 이식용) -->

# 용어 SSOT — 화면 표기 단일 원장

> 기준 문서. `_KIT.md` §4 워크스페이스 캐논 · `cross-audit-notes.md` 교차 감사 결과.
> 대상. `screen-01` ~ `screen-17` 17벌.
> 작성 원칙. **화면이 실제로 인쇄하는 값만 담는다.** 모든 값에 `파일명:줄번호` 근거를 단다. 두 화면이 다른 값을 말하면 그 사실을 적고 어느 쪽이 SSOT 인지 근거와 함께 판정한다.

---

## 0. 이 문서가 필요한 이유 (실제 코드 근거)

한국어 매핑이 라우트 폴더 안에 갇혀 있어 재사용이 불가능하다. 실측 결과 셋.

| 사실                                                                     | 근거                                                                                                |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| 주문 상태 한국어 매핑 `STATE_META` 가 라우트 `_components` 안에 있다     | `frontend/src/app/(dashboard)/orders/_components/orders-blotter.tsx:33-42`                          |
| 그래서 같은 enum 을 쓰는 `OrdersPanel` 은 원시 enum 을 그대로 인쇄한다   | `frontend/src/features/trading/components/orders-panel.tsx:113` `{o.side}` · `:115` `{o.state}`     |
| 옵티마이저 목록 헤더 5개가 전부 영문이고 상태·목표 지표도 원시 enum 이다 | `frontend/src/app/(dashboard)/optimizer/_components/optimizer-run-list.tsx:78-82` · `:117` · `:121` |

같은 병이 다른 곳에도 있다. `ParsePreviewResponse["status"]` 매핑이 두 파일에 복제됐고 값까지 갈렸다. `ok` 가 한쪽은 `변환 완료`(`frontend/src/app/(dashboard)/strategies/new/_components/parse-result-panel.tsx:211`), 다른 쪽은 `변환 가능`(`frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-panel.tsx:221`) 이다.
백테스트 상태도 배지와 필터가 갈렸다. `queued` 가 배지에선 `대기 중`(`frontend/src/app/(dashboard)/backtests/_components/status-badge.tsx:10`), 필터 탭에선 `대기`(`frontend/src/app/(dashboard)/backtests/_components/backtest-list.tsx:33`) 다. `cancelled` 도 `취소됨` 대 `취소` 로 갈린다.

좋은 선례는 이미 있다. `frontend/src/features/onboarding/types.ts:15-20` 의 `ONBOARDING_STEP_LABEL` 은 도메인 폴더에 있고, enum 유니온과 `Record` 가 한 파일 안에서 붙어 있어 enum 추가 시 누락이 타입 에러로 잡힌다. 이 문서는 그 형태를 나머지 도메인으로 확장하는 규약이다.

---

## 1. 확정 대조표

톤 표기는 프로토타입 셸 클래스명이다. `chip` 은 중립, `chip done` 은 완결, `chip accent` 은 진행·활성이다. 경고·실패 톤의 **실제 클래스명은 `chip failed`** 이며(4파일), `chip warn` 은 `screen-08` 1파일에만 있다. 이름을 `warn` 으로 통일하자는 것은 §3-1 의 **판정이자 미결 항목**(§6-5)이고 아직 화면에 반영되지 않았다. 아래 표의 톤 열은 판정이 아니라 **실측 클래스명**을 적는다.

> 좌표 기준. 2026-07-20 화면 교정 반영 후 재실측. `screen-01` `screen-02` `screen-03` `screen-04` `screen-06` `screen-09` `screen-10` `screen-11` `screen-12` `screen-14` `screen-15` `screen-16` `screen-17` 이 이 라운드에서 바뀌었다.

### 1-A. 이미 17화면이 일치 — 그대로 승격

| enum                 | 한국어        | 실측 톤 클래스              | 근거                                                                                                                                                                     |
| -------------------- | ------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `run.queued`         | 대기          | `chip`                      | `screen-03-backtests-list.html:1355` · 상태 필터 옵션 `screen-03-backtests-list.html:1220` · `screen-09-optimizer-list.html:1296`                                        |
| `run.completed`      | 완료          | `chip done` (체크 svg 포함) | `screen-03-backtests-list.html:1340` (03 에서 7행) · `screen-09-optimizer-list.html:1323` (09 에서 5행) · `screen-02-dashboard.html:1321` (02 에서 3행) · 15건 전부 일치 |
| `run.failed`         | 실패          | `chip failed`               | `screen-03-backtests-list.html:1422` · `screen-02-dashboard.html:1413` · `screen-09-optimizer-list.html:1346`                                                            |
| `order.pending`      | 대기          | `chip`                      | `screen-11-orders.html:1290` (11 에서 3곳 · 1290/1318/1388)                                                                                                              |
| `order.submitted`    | 전송          | `chip`                      | `screen-11-orders.html:1304` (11 에서 3곳 · 1304/1332/1402)                                                                                                              |
| `order.filled`       | 체결          | `chip done` (체크 svg 포함) | `screen-11-orders.html:1360` · `:1416` (1페이지 2건. 나머지 3건은 2페이지)                                                                                               |
| `order.rejected`     | 거부          | `chip failed`               | `screen-11-orders.html:1346`                                                                                                                                             |
| `order.cancelled`    | 취소          | `chip`                      | `screen-11-orders.html:1374`                                                                                                                                             |
| `strategy.draft`     | 초안          | `chip`                      | `screen-06-strategies-list.html:1302` (06 에서 4곳 · 1302/1448/1468/1488) · `screen-02-dashboard.html:1519` · `screen-07-strategy-create.html:1198`                      |
| `side.long`          | 롱            | `.side.long`                | `screen-01-trading-cockpit.html:1238` · `screen-04-trade-detail.html:1265` · 롱 12건(01 에서 4 + 04 에서 8) / 숏 5건(01 에서 2 + 04 에서 3) 전부 일치                    |
| `side.short`         | 숏            | `.side.short`               | `screen-04-trade-detail.html:1274` · 셀렉트 옵션 `screen-04-trade-detail.html:1234-1235`                                                                                 |
| `order.side.buy`     | 매수          | `.order-side.buy`           | `screen-11-orders.html:1301` (11 에서 6곳)                                                                                                                               |
| `order.side.sell`    | 매도          | `.order-side.sell`          | `screen-11-orders.html:1287` (11 에서 4곳)                                                                                                                               |
| `direction.maximize` | 최대화        | 없음                        | `screen-09-optimizer-list.html:1218` 셀렉트 옵션 · `screen-10-optimizer-detail.html:1639`                                                                                |
| `direction.minimize` | 최소화        | 없음                        | `screen-09-optimizer-list.html:1219` 셀렉트 옵션 · `screen-09-optimizer-list.html:1343`                                                                                  |
| `method.bayesian`    | 베이지안 탐색 | 없음                        | `screen-09-optimizer-list.html:1201` 셀렉트 옵션 · `screen-09-optimizer-list.html:1330`                                                                                  |
| `method.genetic`     | 유전 알고리즘 | 없음                        | `screen-09-optimizer-list.html:1202` 셀렉트 옵션 · `screen-09-optimizer-list.html:1305`                                                                                  |
| `reduce_only`        | 감소전용      | `chip chip-xs`              | `screen-11-orders.html:1287` · `:1315` · `:1371` · `:1413` · 4건 전부 title 문구까지 바이트 동일                                                                         |
| `execution.mock`     | 모의          | `chip chip-xs`              | `screen-11-orders.html:1404` · 범례 `screen-11-orders.html:1484`                                                                                                         |
| `order_id.broker`    | 브로커        | `chip chip-xs`              | `screen-11-orders.html:1306` (5곳 · 1306/1334/1362/1376/1418) · 범례 `screen-11-orders.html:1484`                                                                        |
| 총 항목 22종         |               |                             | 반례 0건                                                                                                                                                                 |

### 1-B. 충돌 항목 — 이번에 확정

각 행은 **선택한 표기 / 탈락한 변종 / 실측 근거** 순이다.

#### B1. `run.running` = 실행 중 · `chip accent` — **미해소**

- 탈락. `chip`(중립) 톤.
- 실측. `chip accent` = `screen-03-backtests-list.html:1374` · `screen-09-optimizer-list.html:1310` (2곳). `chip` = `screen-02-dashboard.html:1358` · `screen-02-dashboard.html:1374` (2곳). 라벨 `실행 중` 자체는 4건 전부 동일하다.
- 근거. 2 대 2 다수결이 아니다. 백테스트 실행 상태의 원장은 **상태 필터 셀렉트(`screen-03-backtests-list.html:1215-1221`, `aria-label="상태 필터"` · 옵션 5개 = `상태 전체` + 상태 4종 `완료`/`실행 중`/`실패`/`대기`)** 와 그 상태 4종을 표에서 실제로 렌더하는 `screen-03` 이고 그쪽이 accent 다. 최적화 원장 `screen-09` 도 서로 참조 없이 같은 accent 에 도달했다. `screen-02` 는 두 원장을 합쳐 보여 주는 파생 화면이며 자기 주석(`screen-02-dashboard.html:1706-1707`)에서 출처가 `screen-03` + `screen-09` 라고 스스로 밝힌다.
- 좌표 정정 기록. 이전 판본은 이 셀렉트를 `screen-03-backtests-list.html:1225-1230` 이라고 적었으나 그 구간은 `aria-label="기간 필터"` 셀렉트(`1223-1228`)다. B1 확정의 유일한 근거였으므로 `1215-1221` 로 고쳤다.
- 고칠 파일. `screen-02-dashboard.html:1358` · `:1374`. 2026-07-20 라운드에서 아직 손대지 않았다.

#### B2. `strategy.deployed` = 배포됨 · `chip accent` — **[해소됨] 2026-07-20**

- 탈락. `chip done`, `chip`(중립). 세트에서 가장 심한 3-way 분기였다.
- 이전 상태. `chip accent` 3곳 · `chip done` 2곳(`screen-01`) · `chip`(중립) 2곳(`screen-02`).
- 조치. `screen-01-trading-cockpit.html:1279` `:1300` 을 `chip done` 에서 `chip accent` 로, `screen-02-dashboard.html:1447` `:1495` 를 중립 `chip` 에서 `chip accent` 로 바꿨다.
- 현재 실측. `chip accent` = `screen-01-trading-cockpit.html:1279` · `:1300` · `screen-02-dashboard.html:1447` · `:1495` · `screen-06-strategies-list.html:1260` · `:1322` · `screen-08-strategy-editor.html:1233`. **7건 전부 `chip accent`, 반례 0건.**
- 근거 넷. (1) 전략 상태 원장은 12행 전수를 상태 칩과 함께 렌더하는 `screen-06`(1260~1488)이고 accent 다. (2) 전략 편집 화면 `screen-08` 이 독립적으로 같은 accent 에 도달했다. (3) `chip done` 은 `--bull` 계열이라 같은 화면의 손익 색과 시각적으로 충돌하고, `_KIT.md:79` 색 규율 "초록/빨강은 손익 숫자에만" 과 어긋난다. `screen-01-trading-cockpit.html:1659` 가 이 교체 근거를 자기 감사 주석에 적었다. (4) 교정 전 `screen-02` 의 중립 `chip` 은 배포됨·검증됨·초안 세 상태를 모두 같은 톤으로 인쇄해 상태 구분 정보를 아예 잃었다.

#### B3. `strategy.validated` = 검증됨 · `chip done` — **[해소됨] 2026-07-20**

- 탈락. `chip`(중립).
- 이전 상태. `chip done` 6곳(`screen-06`) 대 중립 `chip` 1곳(`screen-02`).
- 조치. `screen-02-dashboard.html:1471` 을 중립 `chip` 에서 `chip done` 으로 바꿨다.
- 현재 실측. `chip done` = `screen-02-dashboard.html:1471` · `screen-06-strategies-list.html:1281` `:1343` `:1364` `:1385` `:1406` `:1427`. **7건 전부 `chip done` 이고 7건 전부 체크 svg 가 없다.** 반례 0건.
- 근거. 12행 전부를 렌더하는 원장이 `screen-06` 이다. `screen-02:1445-1522` 는 대표 4종만 뽑은 파생 카드다.
- 주의. `chip done` 이 `run.completed` · `order.filled` 에서는 체크 svg 를 갖고 `strategy.validated` 에서는 7건 전부 갖지 않는다. 아이콘 유무는 톤이 아니라 항목별 속성으로 분리해 관리한다.

#### B4. `grid_search` = 그리드 탐색 — **[해소됨] 2026-07-20**

- 탈락. `격자`, `격자 탐색`, 축약 `그리드`.
- 조치. `screen-12-onboarding.html:1555` 의 `이동평균 길이 두 개를 격자로 훑어` 를 `그리드로 훑어` 로 바꿨다.
- 현재 실측. 완전형 `그리드 탐색` = `screen-09-optimizer-list.html:1200` 셀렉트 옵션 · `:1291` `:1319` `:1366` · `screen-10-optimizer-detail.html:1221` `:1248`. **폐기 표기 `격자` 는 노출 카피 0건** 이고, `screen-10-optimizer-detail.html:1908` 감사 주석의 해소 기록 1건만 남았다. 축약 `그리드` 단독 = `screen-12-onboarding.html:1555` `:1556` · `screen-14-landing.html:1367` `:1368` · `screen-16-pricing.html:1260` `:1392` · `screen-17-waitlist.html:1353`.
- 근거. `screen-10-optimizer-detail.html:1908` 이 `grid_search  -> "그리드 탐색" 으로 고정. "격자" 표기는 전부 제거했고, 3 x 3 배치를 가리킬 때는 "히트맵" 을 쓴다.` 라고 선언했다. 마케팅·온보딩 화면의 축약형은 3방식 나열 문맥의 생략이라 별도 enum 이 아니라 표기 축약이며, 라벨을 하나로 잠그면 자동 해소된다.

#### B5. `sharpe_ratio` = 샤프 지수 (표 헤더 축약은 `abbr="샤프"`)

- 탈락. `샤프` 단독 표기.
- 실측. `샤프 지수` = `screen-09-optimizer-list.html:1209` 셀렉트 옵션(09 전역 4행) · **`screen-10-optimizer-detail.html` 전역 24행 = 노출 카피 16행(1259/1264/1271/1304/1309/1323/1415/1427/1443/1529/1535/1561/1602/1603/1613/1639) + 감사 주석 8행(1825/1847/1848/1852/1854/1862/1906/1918)**. 한 행에 2회 인쇄하는 곳이 2행(`:1309` `:1427`)이라 문자열 출현 수로 세면 26회다. `screen-03-backtests-list.html:1308` · `screen-06-strategies-list.html:1248` 은 `aria-label` 로 완전형을 쓴다. 시각 텍스트 `샤프` 단독 = `screen-02-dashboard.html:1458` `:1482` `:1506` `:1530` · `screen-03-backtests-list.html:1309` · `screen-06-strategies-list.html:1248`.
- 좌표 정정 기록. 이전 판본의 "전역 16곳" 은 `screen-10` 본문만 센 값이었다. 감사 주석까지 포함한 파일 전역은 24행이다. 두 숫자를 함께 적어 어느 모집단인지 못 헷갈리게 한다.
- 근거 셋. (1) 사용자가 목표 지표를 실제로 선택하는 곳이 `screen-09:1209` 이고 완전형이다. (2) `screen-03-backtests-list.html:1308` 이 이미 `aria-label="샤프 지수 기준 정렬"` 로 접근성 이름에 완전형을 쓰면서 시각 텍스트(`:1309`)만 줄였다. 완전형이 정본이고 축약은 폭 제약임을 그 화면이 스스로 인정한다. (3) `screen-06-strategies-list.html:1248` 이 이번 라운드에 `aria-label="샤프 지수"` 를 얻어 같은 형태로 정렬됐다.
- 축약 허용 자리는 표 헤더 하나뿐이고, 방식은 `screen-02-dashboard.html:1307` 의 `abbr` 속성 패턴 또는 `screen-06:1248` 의 `aria-label` 패턴을 쓴다.

#### B6. `max_drawdown` = 최대 낙폭 (표 헤더 축약은 `abbr="MDD"`)

- 탈락. `MDD` 단독 시각 텍스트, `낙폭`.
- 실측. `최대 낙폭` = `screen-02-dashboard.html:1307`(th 텍스트 + `abbr="MDD"`) · `screen-09-optimizer-list.html:1211` · `screen-10-optimizer-detail.html:1325` · `screen-14-landing.html:1323` · `screen-03-backtests-list.html:1302`(aria-label) · `screen-06-strategies-list.html:1247`(aria-label). 시각 텍스트 `MDD` 단독 = `screen-03-backtests-list.html:1303` · `screen-06-strategies-list.html:1247`. 축약 `낙폭` = `screen-12-onboarding.html:1565` 서술문.
- 근거. `screen-02-dashboard.html:1307` 의 `<th scope="col" class="num" abbr="MDD">최대 낙폭</th>` 하나가 "시각 텍스트는 완전형 + `abbr` 로 축약" 이라는 정답 형태를 이미 구현했다. `screen-03:1302` 는 정렬 버튼 `aria-label` 에만 완전형을 쓰고 `abbr` 이 없다. `screen-06:1247` 은 이번 라운드에 `aria-label="최대 낙폭"` 을 얻어 접근 가능한 이름은 확보했으나 `abbr` 은 여전히 없다.
- 남은 교정 2건. `screen-03-backtests-list.html:1303` · `screen-06-strategies-list.html:1247` 의 시각 텍스트. 둘 다 `screen-02:1307` 형태로.

#### B7. `total_return` = 총 수익률 (표 헤더 축약은 `abbr="수익률"`)

- 탈락. `수익률` 단독 시각 텍스트.
- 실측. `총 수익률` = `screen-09-optimizer-list.html:1210` 셀렉트 옵션 · `screen-10-optimizer-detail.html:1278` `:1310` `:1324` · `screen-12-onboarding.html:1388` `:1506` · `screen-14-landing.html:1315`. 시각 텍스트 `수익률` 단독 = `screen-02-dashboard.html:1306` · `screen-03-backtests-list.html:1297`.
- 근거. 목표 지표 셀렉트가 완전형이다.
- **동명이의 분리 의무.** 아래 셋은 `total_return` 이 아니라 각각 다른 enum 이다. 합치면 같은 값처럼 오독된다.
  - `position.unrealized_return` = 미결제 포지션의 진입가 대비 등락률. `screen-01-trading-cockpit.html:1228` th `수익률`, 계산식 `screen-01-trading-cockpit.html:1257` `수익률은 677.00 / 62,880.00 = 1.0767%`.
  - `trade.realized_return` = 거래 단위 실현 수익률(비용 차감 후). `screen-04-trade-detail.html:1407` th·값 `실현 수익률` `+3.76%`, 검산 `:1411`. 같은 화면 `:1258` 열 이름 `변동률` 은 비용 제외 총변동률이라 또 다른 필드다.
  - `strategy.last_run_return` = 전략의 가장 최근 완료 백테스트 1건 기준 수익률. `screen-06-strategies-list.html:1246` th `최근 수익률`.
- 고칠 파일. `screen-02-dashboard.html:1306` · `screen-03-backtests-list.html:1297` 두 곳만이 진짜 충돌이다.

#### B8. 도메인명 `optimizer` = 페이지명 `옵티마이저` / 동작 `최적화`

- 탈락. `최적화` 단일화(교차 감사 초기 권고), `파라미터 최적화`.
- 실측. 페이지 정체성 = `옵티마이저`. nav `aria-label="옵티마이저"` 가 사이드바 보유 13화면 전부 동일(`screen-01-trading-cockpit.html:1067`), `screen-09-optimizer-list.html:19` title, `:1131` breadcrumb, `:1157` h1, `:1498` 푸터. 실행 유형·동작 = `최적화`. `screen-09-optimizer-list.html:1179` 섹션 제목 `최적화 제출`, `screen-16-pricing.html:1392`.
- 근거. 교차 감사의 "최적화 단일화" 권고는 반영되지 않았고 오히려 `screen-09-optimizer-list.html:1563` 이 `페이지 이름 SSOT = nav aria-label · <title> · breadcrumb · h1 · 푸터 모두 "옵티마이저" 1개 단어` 를 자기 규율로 선언했다. 실측이 권고와 어긋나므로 역할 분리로 재판정한다. 도메인·페이지명은 nav 13벌이 반례 없이 `옵티마이저` 이고, 동사·실행 유형은 `_KIT.md:161` "버튼 라벨은 동사" 규약과 `최적화 실행` 이 정합한다.
- 잔여 교정 1건. `screen-10-optimizer-detail.html:19` title 이 `옵티마이저 실행 상세` 인데 `:1221` h1 이 `MA Crossover Strategy 그리드 탐색` 이라 `screen-09:1563` 이 세운 5축 일치 규율을 홀로 깬다. 2026-07-20 라운드에서 손대지 않았다.

#### B9. 도메인명 `orders` = 주문 — **[일부 해소] 2026-07-20**

- 탈락. `주문 내역`, `주문 원장`.
- 이전 상태. 3-way 분기가 전부 `screen-11` 한 파일 안에서 일어났다. `주문` = nav + title + breadcrumb. `주문 내역` = h1 + 섹션 aria-label. `주문 원장` = 섹션 제목 + 카드 제목 + 표 aria-label + 푸터.
- 조치. h1 `주문 내역` 을 `주문` 으로, 섹션 `aria-label="주문 내역 개요"` 를 `주문 개요`(`screen-11-orders.html:1176`)로 바꿨다. 데이터 출처를 가리키는 `주문 원장` 표현은 의도적으로 유지했다.
- 현재 실측. `주문` = nav 13벌(`screen-01-trading-cockpit.html:1075`) + `screen-11-orders.html:19` title + `:1153` breadcrumb + `:1176` 섹션 aria-label + `:1179` h1. **`주문 내역` 은 17벌에 0건.** `주문 원장` = `:1238` 섹션 aria-label + `:1241` 섹션 제목 + `:1248` 카드 제목 + `:1266` 표 aria-label + `:1586` 푸터.
- 남은 불일치 1건. `screen-09:1563` 의 5축 규율 중 푸터(`screen-11:1586` `QuantBridge · 주문 원장 · 14건`)만 페이지명이 아니라 데이터 출처 표현을 쓴다. 다른 목록 화면(`screen-03:1629` `백테스트 목록`, `screen-09:1498` `옵티마이저`)은 페이지명을 쓴다. 이식 시 `주문` 으로 맞추는 것이 5축 규율에 정합한다.
- 근거 셋. (1) nav 라벨이 13벌 전부 `주문` 이고 반례가 없다. (2) `screen-09:1563` 이 세운 5축 일치 규율. (3) `원장` 은 `screen-02-dashboard.html:1293` `:1421` 에서 "백테스트 원장 / 최적화 원장" 처럼 데이터 출처를 가리키는 서술어로 이미 쓰이므로 페이지명으로 승격하면 그 용법과 충돌한다.

#### B10. 도메인명 `trade` = 거래

- 탈락. `트레이드 상세`.
- 실측. `<title>` 만 홀로 `트레이드 상세`(`screen-04-trade-detail.html:19`)이고 breadcrumb · h1 · 푸터 · 섹션 aria-label(`:1214` `거래 목록과 선택된 거래 상세` · `:1377` `186번 거래 상세`)은 전부 `거래` 계열이다.
- 근거. 4 대 1 다수결이 아니라 (1) 사용자에게 보이는 축(breadcrumb·h1·푸터)이 전부 `거래` 이고, (2) 세트 전체가 외래어 음차 대신 한국어를 쓰는 규율(th 헤더 약 120개 전부 한국어)이다.
- 주의. nav 의 `트레이딩`(`screen-01-trading-cockpit.html:1069`)은 라이브 세션 도메인이라 `trade` 와 다른 enum 이다. 통합 대상이 아니다.
- 고칠 파일. `screen-04-trade-detail.html:19`. 2026-07-20 라운드에서 손대지 않았다.

#### B11. 백테스트 신규 실행 화면명 = 새 백테스트

- 탈락. `백테스트 설정`, `새 실행`.
- 실측. `백테스트 설정` = `screen-05-backtest-setup.html:10` title. `새 실행` = `:1237` breadcrumb. `새 백테스트 실행` = `:1263` h1. `새 백테스트` = `screen-03-backtests-list.html:1236` 진입 버튼.
- 근거. 사용자가 먼저 읽는 라벨이 진입 버튼이다. h1 만 동사형 `새 백테스트 실행` 을 유지하는 것이 `_KIT.md:161` 과 정합한다.

#### B12. `execution_mode` 3단 분리 = 모의 / 데모 / 라이브

- 확정 사유. 세 단계가 서로 다른 개념인데 한 자리에서 정의한 화면이 없다.
- 실측. `모의` = 로컬 목 어댑터. `screen-11-orders.html:1404` title `거래소를 붙이지 않고 로컬 목 어댑터로 실행한 주문입니다. 실제 거래소에는 나가지 않았습니다.` `데모` = Bybit 데모 계정. `screen-01-trading-cockpit.html:1341` 계정 모드 행 · `:1553` `데모는 실거래와 같은 코드 경로를 쓰지만 슬리피지와 체결 지연은 다르게 나타납니다.` `라이브` = 실자금. `screen-11-orders.html:1563` 카드 제목 `라이브 세션 주문` · `screen-16-pricing.html:1487` `라이브 주문은 실제 자금을 움직이고 손실은 사용자 책임입니다.`
- 근거. 세 값이 서로 충돌하지는 않지만 `execution_mode: mock | demo | live` 로 승격하지 않으면 이식 중 뭉개진다. 특히 `모의`(어댑터 축)와 `데모`(계정 축)는 직교하는 축이므로 하나의 필드로 합치면 안 된다.

#### B13. 거래소 데모 표기 = `Bybit 데모` (한글)

- 탈락. `Bybit Demo`(영문).
- 실측. 한글 `Bybit 데모` = `screen-11-orders.html:1182` · `screen-02-dashboard.html:1211` · `screen-01-trading-cockpit.html:1168` · `screen-14-landing.html:1266` `:1386` · `screen-16-pricing.html:1262` `:1404` · `screen-17-waitlist.html:1204`. 영문 `Bybit Demo` = `screen-12-onboarding.html:1575` 노출 카피 1건 + 같은 파일 헤더 주석 `:33` 1건.
- 근거. 한글 8 대 영문 1 이고, `screen-14-landing.html:1386` 이 이번 라운드에 `Bybit Demo · Bybit Mainnet` 을 `Bybit 데모 · Bybit 메인넷` 으로 바꿔 마케팅 축도 한글로 넘어왔다. 다만 `screen-12-onboarding.html:33` 파일 헤더 주석이 `거래소 주장은 데모 CTA 의 "Bybit Demo 한정" 하나로 제한한다` 로 의도적 문구임을 밝히므로, 표기 통일 시 그 주석도 함께 갱신해야 한다.
- 고칠 파일. `screen-12-onboarding.html:1575` + 헤더 주석 `:33`. 2026-07-20 라운드에서 손대지 않았다.

#### B14. 킬 스위치 라벨 = 상태 `킬 스위치` / 버튼 `긴급 정지`

- 실측. 상태 행 `screen-01-trading-cockpit.html:1336` `<span class="trust-key">킬 스위치</span><span class="trust-val">대기</span>`. 버튼 `screen-01-trading-cockpit.html:1154` `긴급 정지` + `:1157` `긴급 정지는 모든 포지션 시장가 청산 후 세션 중지. 되돌릴 수 없습니다.` 마케팅 `screen-17-waitlist.html:1368` 은 다시 `킬 스위치`.
- 판정. 값 `대기` 의 SSOT 는 상태 행을 실제로 렌더하는 `screen-01:1336` 이다. 라벨은 한 제품 안에서 두 이름이 같은 기능을 가리키므로 이식 전에 하나로 잠가야 한다. `_KIT.md:161` "버튼 라벨은 동사" 규약에 따라 **기능명은 `킬 스위치`, 버튼 라벨만 동사형 `긴급 정지`** 로 역할 분리한다. B8 과 같은 패턴이다.

### 1-C. 화면 간 값 충돌 — 용어가 아니라 사실이 갈린 것

**7행 전부 2026-07-20 라운드에서 해소됐다. 미해소 0건.** 아래는 해소 기록이며, 같은 충돌이 재발했는지 판별하는 회귀 검사 목록으로 쓴다.

| 항목                   | 확정 SSOT                                                                                                    | 이전에 어긋났던 쪽                                                            | 해소 확인 (2026-07-20 재실측)                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 백테스트 상태 분포     | `screen-03` 완료 45 / 실행 중 1 / 실패 1 / 대기 1 = 48 (`screen-03-backtests-list.html:1284`)                | `screen-02` 가 41 / 2 / 3 / 2 를 인쇄                                         | `41 / 2 / 3 / 2` 조합 **17벌 0건**. `screen-02-dashboard.html:1180` `:1421` `:1555` 가 전부 완료 45 · 실행 중 1 · 실패 1 · 대기 1 = 48 로 원장과 일치. 두 파일의 자기 검산도 정합(`screen-03:1668` · `screen-02:1676`)                                                                                                                                                                                                                                                                                   |
| 미완료 실행 3행        | `screen-03` 의 `run_c268af`(실행 중 4h 18%) · `run_5b77`(실패) · `run_b0e7d2`(대기)                          | `screen-02` 의 `run_7f31d0`(1m 64%) · `run_2a55c8` · `run_0c9e14`             | 세 실행 ID **17벌 0건**(`run_0c9e14` 는 `screen-09:1342` 최적화 대상으로만 존재하고 `screen-02` 에는 없음). 봉 수 `770,458` `1,203,840` 도 노출 카피 0건이고 `screen-02:1728` 감사 주석의 해소 기록 1건만 남았다. `screen-02:1360-1361` 이 원장 값 18% 만 인쇄하고 미터 width 와 인쇄값이 일치                                                                                                                                                                                                           |
| `run_c3e77a` 전략 귀속 | MA Crossover Strategy(strat_7a31). `screen-03-backtests-list.html:1432`                                      | `screen-02` 가 Donchian Breakout 에 귀속하며 +58.63% / 1.18 인쇄              | `screen-02:1517-1534` 가 Donchian 행을 `완료된 실행 0건` 칩 + 성과 2칸 무데이터 + 사유 문장으로 되돌렸다. 해소 근거는 `screen-02:1743-1745` 에 기록. `screen-06:1305-1307` 의 strat_4e18 무데이터 3칸과도 정합                                                                                                                                                                                                                                                                                           |
| 그리드 조합 상한       | 9조합. `screen-09-optimizer-list.html:1231`                                                                  | `screen-12-onboarding.html` 이 `그리드 81조합 (9 x 9)` 인쇄                   | `81조합` · `9 x 9` **17벌 0건**. `screen-12:1556` = `그리드 9조합 (3 x 3)`, 자기 검산 `:1687` = `3 x 3 = 9`. 실 코드 상한(`backend/src/optimizer/engine/grid_search.py:52` `_MAX_GRID_CELLS: Final[int] = 9`)과 일치                                                                                                                                                                                                                                                                                     |
| 세션 체결 건수         | 체결 5 / 전체 14. `screen-11-orders.html:1220` `:1654` · `screen-01-trading-cockpit.html:1367`               | `screen-11` 이 체결 3 / 전체 12 를 인쇄해 `screen-01` 의 체결 5 와 어긋남     | **원장 쪽을 늘려 해소.** 판정 근거는 포함 관계다. 세션이 낸 체결은 반드시 주문 원장 안에 있어야 하고, `screen-01:1464` 의 `오늘 실현 손익 +50.91 과 -12.36 을 더하면 01 계좌의 +38.55 가 됩니다.` KPI 체인이 두 청산 체결에 묶여 있어 코크핏 쪽을 줄일 수 없었다. 원장을 12건에서 14건으로 확장(12 - 2 제거 + 4 추가)했고 전체 14 = 체결 5 + 대기 4 + 전송 3 + 취소 1 + 거부 1. `screen-11:1732` 에 코크핏 05 표 5행 ↔ 원장 행 1대1 대응표와 방향 변환 규칙을 신설했다. 두 파일 모두 `미해소` 문자열 0건 |
| 거래소 지원 현황       | OKX = 로드맵. `screen-14-landing.html:1473` `:1479` `:1485` · `screen-17-waitlist.html:1408` `:1414` `:1420` | `screen-16-pricing.html` 이 OKX 를 "연결해 본" 으로 분류                      | `screen-16-pricing.html:1451` = `연결해 본 거래소는 Bybit (데모 · 메인넷) 하나입니다. OKX 와 Binance 와 Bitget 은 로드맵이며 아직 연결하지 않았습니다.` 로 교정. 비교표(`:1270` `:1416`)도 로드맵 칩. 앱 화면 12벌 Bybit 단일 및 `screen-05-backtest-setup.html:1422` 와 정합. **단 실 코드는 여전히 `bybit` + `okx`(`frontend/src/features/trading/schemas.ts:71`)이므로 §6-4 는 미해결로 남는다**                                                                                                      |
| 에러 경로 규약         | `/backtests/{run_id}` + `run_` 접두어 유지. `screen-13-error-pages.html:1168`                                | `screen-04-trade-detail.html:1540` 이 `GET /runs/2f9c41/trades/186/bars` 인쇄 | `screen-04-trade-detail.html:1540` = `GET /backtests/run_2f9c41/trades/186/bars · 504` 로 교정. 파일 전체 `/runs/` 형태 **0건**. `screen-02:1738` 의 규약 선언 및 `screen-02` 의 `GET /backtests/run_2f9c41/summary · 502` 와 정합                                                                                                                                                                                                                                                                       |

> 남은 교차 불일치 1건은 §1-C 항목이 아니라 §6-3 소속이다. `screen-06-strategies-list.html:1669-1672` 이 자기 감사 주석에 `strat_4e18` 의 백테스트 건수(이 화면 0건 대 실행 원장 완료 2건)를 미해소로 적어 두었다. 맞추려면 nav-count 캐논 48 을 12행에 다시 배분해야 하므로 화면 교정이 아니라 사람 결정이 필요하다.

### 1-D. 무데이터 사유 문구 (그대로 승격)

값 없음 셀의 `title` 은 상태별로 다른 문구를 쓴다. 화면 간 불일치 0건이다.

| 상황                         | 문구                                                                                                  | 근거                                                                                       |
| ---------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 대기 실행                    | `아직 실행이 시작되지 않았습니다.`                                                                    | `screen-03-backtests-list.html:1350-1353` · `screen-02-dashboard.html:1333-1334`           |
| 대기 실행 (진행 보조)        | `시작 시각이 아직 없습니다. 대기열 순번은 서버가 보고하지 않습니다.`                                  | `screen-03-backtests-list.html:1357` · `screen-09-optimizer-list.html:1297` 바이트 동일    |
| 실행 중 실행                 | `실행이 끝나야 계산됩니다.`                                                                           | `screen-03-backtests-list.html:1369-1372` · `screen-02-dashboard.html:1355-1356`           |
| 실패 실행                    | `Bybit OHLCV 수집이 중단되어 실행이 완료되지 않았습니다.` (보조 `데이터 수집 단계에서 중단`)          | `screen-03-backtests-list.html:1417-1420` · `:1424` · `screen-02-dashboard.html:1411-1412` |
| 최적화 실행 중               | `실행이 끝나야 결과가 저장됩니다. 서버는 중간 최고값을 보고하지 않습니다.`                            | `screen-09-optimizer-list.html:1308` · `screen-02-dashboard.html:1372-1373`                |
| 최적화 실패                  | `파라미터 공간의 하한이 상한보다 커서 탐색 범위를 만들지 못했고, 평가가 한 번도 실행되지 않았습니다.` | `screen-09-optimizer-list.html:1344`                                                       |
| 축퇴 셀                      | `거래가 0건이라 샤프 지수를 계산할 표본이 없습니다.`                                                  | `screen-10-optimizer-detail.html:1415` · `:1561`                                           |
| 순위 없음                    | `거래가 0건이라 순위를 매길 근거가 없습니다.`                                                         | `screen-10-optimizer-detail.html:1412`                                                     |
| 전략 성과 없음               | `아직 백테스트를 실행하지 않았습니다.`                                                                | `screen-06-strategies-list.html:1305-1307` (06 에서 4행 x 3칸 = 12셀)                      |
| 체결가 없음                  | `아직 체결되지 않아 체결가가 없습니다.`                                                               | `screen-11-orders.html:1289` · `:1317` · `:1387`                                           |
| 주문번호 없음 (미발송)       | `아직 거래소로 보내지 않아 주문번호가 없습니다.`                                                      | `screen-11-orders.html:1292` · `:1320` · `:1390`                                           |
| 주문번호 없음 (거부)         | `거래소로 나가기 전에 걸러져서 주문번호가 없습니다.`                                                  | `screen-11-orders.html:1348`                                                               |
| 익절·손절 없음 (거부)        | `거래소로 나가기 전에 걸러져서 익절과 손절도 붙지 않았습니다.`                                        | `screen-11-orders.html:1347`                                                               |
| 청산가 없음                  | `레버리지 1배 · 격리 마진이라 청산가가 없습니다.`                                                     | `screen-01-trading-cockpit.html:1246`                                                      |
| 로드맵 거래소 환경 없음      | `연결 작업을 시작하지 않아 환경을 정하지 않았습니다.`                                                 | `screen-14-landing.html:1474` · `screen-17-waitlist.html:1409` 바이트 동일                 |
| 로드맵 거래소 확인 범위 없음 | `연결 코드가 없어 확인한 범위가 없습니다.`                                                            | `screen-14-landing.html:1476` · `screen-17-waitlist.html:1411` 바이트 동일                 |

`축퇴` 라는 한자어는 CSS 주석(`screen-10-optimizer-detail.html:1122`)과 감사 주석에만 있고 노출 카피에는 0건이다. 코드 식별자로만 쓰고 화면에는 위 문구를 쓴다.

### 1-E. 인쇄 금지 항목

스키마에 대응 필드가 없으므로 인쇄하지 않는다. 근거는 `frontend/src/features/optimizer/schemas.ts:333-346` `OptimizationRunResponseSchema` 의 필드 목록(`id` `user_id` `backtest_id` `kind` `status` `param_space` `result` `error_message` `created_at` `started_at` `completed_at`)이다.

| 금지 항목                             | 대신 인쇄하는 문구                                                                                | 근거                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 대기열 순번                           | `시작 시각이 아직 없습니다. 대기열 순번은 서버가 보고하지 않습니다.`                              | `screen-09-optimizer-list.html:1297` · 판단 근거 `:1547`                       |
| 최적화 진행률 미터                    | `최적화는 서버가 진행률을 보고하지 않아 미터를 그리지 않습니다.`                                  | `screen-02-dashboard.html:1293` (card-sub 마지막 문장)                         |
| 남은 시간 · ETA                       | `실행 중 작업의 남은 시간은 표시하지 않습니다. 서버가 진행 회차를 아직 보고하지 않기 때문입니다.` | `screen-09-optimizer-list.html:1391`                                           |
| 현재 평가 회차 · 중간 최고값          | 무데이터 셀 + `실행이 끝나야 결과가 저장됩니다. 서버는 중간 최고값을 보고하지 않습니다.`          | `screen-09-optimizer-list.html:1308`                                           |
| 처리한 봉 수                          | 진행률 퍼센트만. 봉 수는 인쇄하지 않는다                                                          | `screen-02-dashboard.html:1359` title · 해소 기록 `:1728-1729`                 |
| 맥동 점 · 카운트다운 · aria-live 수치 | 없음. 미터는 완료된 정적 비율만                                                                   | `screen-10-optimizer-detail.html:1912` (감사 주석이므로 노출 카피로 인용 금지) |

---

## 2. 칩 톤 규약

### 2-1. 톤 4종 정의

| 톤                                          | 의미                                             | 색 토큰        | 셸 정의                                                                       |
| ------------------------------------------- | ------------------------------------------------ | -------------- | ----------------------------------------------------------------------------- |
| `chip`                                      | 중립. 아직 결과가 없거나 사용자 행위로 끝난 상태 | `--ink-2` 계열 | `_kit.html:459`                                                               |
| `chip done`                                 | 완결. 결과가 남은 상태                           | `--bull`       | `_kit.html:474`                                                               |
| `chip accent`                               | 진행 중이거나 활성인 상태                        | `--copper`     | `_kit.html:475`                                                               |
| `chip failed` (현행) / `chip warn` (개명안) | 경고. 실패·거부·미저장                           | `--warn`       | 셸 미정의. 화면에는 `failed` 4파일 + `warn` 1파일. §3-1 판정과 §6-5 미결 참조 |

### 2-2. 상태별 확정표

톤 열은 **현재 화면이 인쇄하는 클래스명**이다. 경고 톤의 개명(`failed` -> `warn`)은 §6-5 에서 미결이므로 여기에 선반영하지 않는다.

| enum                                        | 라벨                     | 실측 톤 클래스                                      | 체크 svg |
| ------------------------------------------- | ------------------------ | --------------------------------------------------- | -------- |
| `run.queued` / `optimization.queued`        | 대기                     | `chip`                                              | 없음     |
| `run.running` / `optimization.running`      | 실행 중                  | `chip accent` (`screen-02` 2곳 미교정 · B1)         | 없음     |
| `run.completed` / `optimization.completed`  | 완료                     | `chip done`                                         | **있음** |
| `run.failed` / `optimization.failed`        | 실패                     | `chip failed`                                       | 없음     |
| `order.pending`                             | 대기                     | `chip`                                              | 없음     |
| `order.submitted`                           | 전송                     | `chip`                                              | 없음     |
| `order.filled`                              | 체결                     | `chip done`                                         | **있음** |
| `order.cancelled`                           | 취소                     | `chip`                                              | 없음     |
| `order.rejected`                            | 거부                     | `chip failed`                                       | 없음     |
| `strategy.draft`                            | 초안                     | `chip`                                              | 없음     |
| `strategy.validated`                        | 검증됨                   | `chip done`                                         | 없음     |
| `strategy.deployed`                         | 배포됨                   | `chip accent`                                       | 없음     |
| 부가 배지 `reduce_only` / `mock` / `broker` | 감소전용 / 모의 / 브로커 | `chip chip-xs`                                      | 없음     |
| 편집기 미저장                               | 저장되지 않은 변경 2줄   | `chip warn` (`screen-08-strategy-editor.html:1238`) | 없음     |

### 2-3. 규약 3줄

1. `chip done` 은 값이 남은 완결 상태에만. 체크 svg 는 실행·주문 완결(`run.completed` `order.filled`)에만 붙이고 전략 `검증됨` 에는 붙이지 않는다(`screen-06` 6건 전부 미포함).
2. `chip accent` 는 진행·활성 하나의 의미로만. 코퍼는 `_KIT.md:79` 상 섹션당 주 액션 1개 + 활성 상태 전용이므로, 완결 상태에 accent 를 주면 코퍼가 두 의미를 갖게 된다.
3. `chip done`(초록 계열)을 진행 상태나 배포 상태에 쓰지 않는다. `--bull` 은 손익 데이터 전용 색이다.

### 2-4. 남은 위반 2건 — 전부 `screen-02` 의 `실행 중`

2026-07-20 라운드 이전에는 칩 톤 분기가 7건이었다. `screen-02` 4건(running 2 + deployed 1 + validated 1) + `screen-01` 2건(deployed) + 나머지 1건이다. 이 라운드에서 5건이 닫혔다.

| 항목                                                 | 이전         | 현재          | 상태            |
| ---------------------------------------------------- | ------------ | ------------- | --------------- |
| `screen-01-trading-cockpit.html:1279` `:1300` 배포됨 | `chip done`  | `chip accent` | 해소            |
| `screen-02-dashboard.html:1447` `:1495` 배포됨       | `chip`(중립) | `chip accent` | 해소            |
| `screen-02-dashboard.html:1471` 검증됨               | `chip`(중립) | `chip done`   | 해소            |
| `screen-02-dashboard.html:1358` `:1374` 실행 중      | `chip`(중립) | `chip`(중립)  | **미해소 · B1** |

남은 2건은 파생 화면 `screen-02` 가 원장 `screen-03:1374` · `screen-09:1310` 의 `chip accent` 와 어긋나는 자리다. 이 둘만 고치면 톤 일관성은 전부 닫힌다. 17벌 실측 총계는 `class="chip accent"` 24건 · `class="chip done"` 35건 · `class="chip failed"` 4건 · `class="chip warn"` 1건이다.

---

## 3. CSS primitive 이름 규약

### 3-1. `.chip.failed` 대 `.chip.warn` — `.chip.warn` 으로 통일

- 실측. `.chip.failed` = `screen-02-dashboard.html:1006` · `screen-03-backtests-list.html:1030` · `screen-09-optimizer-list.html:1030` · `screen-11-orders.html:1079` (4파일, 선언 바이트 동일). `.chip.warn` = `screen-08-strategy-editor.html:998-1002` (1파일). 두 선언의 세 속성이 값까지 완전히 같다.
- 사용 빈도만 보면 4 대 1 로 `failed` 가 우세다. 그런데 5개 선언 모두 `color: var(--warn)` / `border-color: rgba(229,169,61,0.4)` / `background: var(--warn-soft)` 로 `--warn` 토큰만 참조한다. 게다가 `screen-08-strategy-editor.html:1238` 의 사용처는 `저장되지 않은 변경 2줄` 이라 실패가 아니다.
- 판정. **`failed` 는 5개 선언 중 4개를 잘못 설명하고 1개 사용처를 완전히 잘못 설명한다. `warn` 은 5개 전부를 정확히 설명한다.** 이름은 토큰을 따라간다. `.chip.warn` 으로 통일하고 `_kit.html` 셸로 승격한다.
- 부작용 없음. `run.failed` `order.rejected` 도 같은 시각 결과를 유지한다. 바뀌는 것은 클래스명뿐이다.
- **반영 상태. 판정일 뿐 미적용이다.** 2026-07-20 재실측 기준 화면이 인쇄하는 클래스는 여전히 `chip failed` 4건(`screen-02:1413` · `screen-03:1422` · `screen-09:1346` · `screen-11:1346`)이고 `chip warn` 1건(`screen-08:1238`)이다. 개명 범위는 §6-5 미결이므로 §1-A · §2-2 의 톤 열에는 실측 클래스명을 적고 이 판정을 선반영하지 않는다.

### 3-2. 셸 미승격 primitive 5종 — `_kit.html` 로 승격

지금은 파일마다 복붙 상태라 다음 화면이 또 갈릴 구조다.

| 클래스                           | 현재 위치                                                                                             | 조치                                                                                                      |
| -------------------------------- | ----------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `.chip.warn`                     | 5파일 중복(§3-1)                                                                                      | 셸 승격                                                                                                   |
| `.chip-xs`                       | `screen-11-orders.html:1078`                                                                          | 셸 승격                                                                                                   |
| `.order-side` / `.buy` / `.sell` | `screen-11-orders.html:1059` `:1070-1071`                                                             | 셸 승격. 지금은 screen-11 전용이라 다른 화면이 주문을 그리면 `.side` 로 회귀한다                          |
| `.meter-void`                    | `screen-12-onboarding.html:1106` **1파일뿐** (사용처 5곳 · `:1390` `:1404` `:1508` `:1515` `:1522`)   | 셸 승격. 교차 감사 렌즈 3 이 이미 권고. 이전 판본의 "외 1벌" 은 오기이며 17벌 재grep 결과 다른 파일에 0건 |
| `.field-error`                   | `screen-05-backtest-setup.html:1036` · `screen-16-pricing.html:1115` · `screen-17-waitlist.html:1085` | 셸 승격                                                                                                   |

### 3-3. 같은 이름 · 다른 값 — 값 SSOT 확정

| 클래스             | 갈린 값                                                                                                                                                                  | 확정                                                                       | 근거                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `.field-error svg` | 13px / stroke 2 / margin-top 3px (`screen-05-backtest-setup.html:1044`) vs 14px / 1.9 / 2px (`screen-16-pricing.html:1116` · `screen-17-waitlist.html:1093`)             | **14px · 1.9 · 2px**                                                       | 2 대 1 이고 두 파일이 서로 참조 없이 같은 값에 도달                              |
| `.input.invalid`   | border-color + `background: var(--warn-soft)` (`screen-05-backtest-setup.html:1035`) vs border-color 만 (`screen-16-pricing.html:1117` · `screen-17-waitlist.html:1084`) | **border-color 만**                                                        | 2 대 1. warn-soft 배경은 `.field-error` 텍스트 색(`--warn`)과 겹쳐 대비를 깎는다 |
| `.btn-xs`          | `padding: 0 11px`(`screen-10-optimizer-detail.html:1017`) vs `0 10px`(5파일 · 01:1009 · 03:1069 · 06:1027 · 09:1051 · 11:1081)                                           | **`0 10px`**                                                               | 5 대 1                                                                           |
| `.field-label`     | 6파일 6값. 아래 표 참조                                                                                                                                                  | **`font-size:0.78rem; font-weight:600; color: var(--ink-2)`** (3속성 코어) | 아래 근거 참조                                                                   |

`.field-label` 은 6개 선언이 전부 다르므로 근거를 속성별로 편다. 이전 판본은 확정값에 `display:block` 을 넣고 그 근거를 "최다 조합(07·16·17)" 이라고 적었는데, 실측하면 07 과 17 에는 `display:block` 이 없다. 근거와 확정값이 어긋나 있었다.

| 파일                                  | 선언 실측                                                                                       |
| ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `screen-05-backtest-setup.html:1017`  | `font-size: 0.8rem; font-weight: 600; color: var(--ink-2)`                                      |
| `screen-07-strategy-create.html:1017` | `font-size: 0.78rem; font-weight: 600; color: var(--ink-2)`                                     |
| `screen-09-optimizer-list.html:1007`  | `font-size: 0.76rem; font-weight: 600; color: var(--ink-3)`                                     |
| `screen-14-landing.html:1156`         | `display: block; font-size: 0.8rem; color: var(--ink-2); margin-bottom: 6px`                    |
| `screen-16-pricing.html:1114`         | `display: block; font-size: 0.78rem; font-weight: 600; color: var(--ink-2); margin-bottom: 6px` |
| `screen-17-waitlist.html:1070`        | `font-size: 0.78rem; font-weight: 600; color: var(--ink-2)`                                     |

- `font-size: 0.78rem` = 3파일(07·16·17) 대 `0.8rem` 2파일(05·14) 대 `0.76rem` 1파일(09). **0.78rem 확정.**
- `font-weight: 600` = 5파일. `screen-14` 만 없다. **600 확정.**
- `color: var(--ink-2)` = 5파일. `screen-09` 만 `--ink-3`. **`--ink-2` 확정.**
- `display: block` + `margin-bottom: 6px` = 14·16 **2파일뿐**이라 다수가 아니다. 확정값 코어에서 뺀다. 다만 `<label>` 은 기본이 인라인이라 `margin-bottom` 이 먹지 않으므로, 셸 승격 시 두 속성을 함께 넣을지는 레이아웃 판단으로 따로 정한다. 값 다수결로는 정당화되지 않는다는 사실만 여기 남긴다.
- 바이트까지 완전히 같은 선언 쌍은 07 == 17 하나뿐이다.

### 3-4. 같은 이름 · 다른 개념 — 분리 개명

React 로 옮겨 CSS 를 한 스코프에 합치는 순간 전부 충돌한다. 이식 전 필수.

| 현재 이름      | 개념 A                                                       | 개념 B                                                                                            | 개명안                               |
| -------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `.calc`        | 검산 문구 인라인 텍스트 (`screen-04-trade-detail.html:1029`) | 계산 요약 그리드 셀 (`screen-05-backtest-setup.html:1086`, 형제 `.calc-label` `.calc-value` 보유) | `.calc-inline` / `.calc-cell`        |
| `.banner`      | 인라인 고지 줄 (`screen-09-optimizer-list.html:1012`)        | 카드형 배너 블록 (`screen-16-pricing.html:1054`)                                                  | `.notice-inline` / `.notice-card`    |
| `.filter-note` | 칩 나열 컨테이너 (`screen-06-strategies-list.html:1002`)     | 단순 텍스트 주석 (`screen-11-orders.html:1021`)                                                   | `.filter-chips-row` / `.filter-hint` |
| `.hero`        | 1단 텍스트 블록 (`screen-16-pricing.html:1042`)              | 2단 그리드 (`screen-17-waitlist.html:1038`)                                                       | `.hero-text` / `.hero-split`         |

### 3-5. 폼 에러 네이밍 계열 정리

- 필드 단위 = `.field-error` (3파일). 유지.
- 폼 단위 = `.auth-alert` + `.auth-alert-title` + `.auth-alert-body` (`screen-15-login.html:1112` `:1122` `:1123`, 형제 `:1121` svg · `:1124` state-code · `:1126` hidden). **`.form-alert` + `.form-alert-title` + `.form-alert-body` 로 개명.**
- 근거. 두 개념은 형제인데 네이밍 계열이 다르고, `auth` 접두어가 도메인에 묶여 있어 재사용이 불가능하다. 교차 감사가 같은 개명을 권고했으나 미반영 상태다(`.form-alert` 는 17벌에 0건).
- 해소 확인 2건. `.form-error` 는 현재 17벌 0건이고 `screen-17-waitlist.html:1083` 이 주석으로 `05 / 16 과 같은 .input.invalid + .field-error 이름을 쓴다` 는 취지를 명시해 정렬을 못박았다(원문은 클래스명을 백틱으로 감싼다). `.field-input.is-invalid` 도 현재 0건이다.

### 3-6. `.tabs` 는 두 컴포넌트로 분리 — **오용 4건 [해소됨] 2026-07-20**

17벌 전수 `role` 실측(파일별 `tabpanel` / `tablist` / `group` 개수)에 근거한 분류다.

| 실제 시맨틱                                               | 화면                                                                                                                                                                                                                                                                                                                                            | 조치                 |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| 진짜 탭 (`role="tabpanel"` 실재)                          | `screen-08-strategy-editor.html:1412-1415` tablist + `:1427` `:1491` `:1561` tabpanel 3개. **17벌 중 이 1파일뿐**                                                                                                                                                                                                                               | `<Tabs>`             |
| 상호배타 토글 (`role="group"` + `aria-pressed`)           | `screen-02-dashboard.html:1215` 표시 기간 · `screen-03-backtests-list.html:1275` 페이지당 표시 개수 · `screen-09-optimizer-list.html:1256` 페이지당 요청 개수 · `screen-10-optimizer-detail.html:1308` 정렬 기준 · `screen-11-orders.html:1218` 주문 상태 필터(CSS 주석 `:1073` 에 판단 근거 기록) · `screen-15-login.html:1286` 인증 방식 선택 | `<SegmentedControl>` |
| **오용.** `role="tablist"` 를 선언했지만 tabpanel 이 없음 | **17벌 0건**                                                                                                                                                                                                                                                                                                                                    | —                    |

#### screen-15 오분류 정정

이전 판본은 `screen-15-login.html:1286-1288` 을 `screen-08` 과 나란히 "진짜 탭" 으로 분류했다. **오류다.** 그 파일에 `role="tabpanel"` 은 처음부터 0건이었고, 문서가 오용으로 지목한 `screen-02` `screen-03` `screen-09` `screen-10` 과 정확히 같은 패턴이었다. 게다가 `screen-15` 의 `aria-controls` 대상 `#auth-form` 은 `<form>` 이라 tab -> tabpanel 관계가 성립하지 않아, 네 화면보다 오히려 더 강한 오용이었다.

2026-07-20 라운드에서 `screen-15` 는 `role="group"` + `aria-pressed`(`:1287` true / `:1288` false)로 교정됐고 `aria-controls` 도 제거됐다. `setMode()`(`:1394`)의 속성 토글도 `aria-selected` 에서 `aria-pressed` 로 함께 바뀌어 마크업과 스크립트가 정합한다. 따라서 현재는 상호배타 토글 6화면 중 하나다.

#### 해소 확인

교정 전 오용 4건(`screen-02` `screen-03` `screen-09` `screen-10`) + 오분류 1건(`screen-15`) = 5화면이 전부 `role="group"` + `aria-pressed` 로 바뀌었다. 각 파일의 토글 스크립트도 `aria-selected` 토글에서 `aria-pressed` 토글로 함께 고쳐, 제거한 속성을 스크립트가 다시 심는 역행이 없다(`screen-02:1648` `:1651` · `screen-03:1644` `:1647` · `screen-09:1513` `:1516` · `screen-10:1789` `:1792` · `screen-15:1394`).

`setAttribute('aria-selected'` 는 17벌에 아직 12곳 남아 있으나 **교정 대상이 아니다.** 내역은 둘로 갈린다.

- `screen-08-strategy-editor.html:1647` `:1650`. 진짜 탭의 핸들러이므로 `aria-selected` 가 정답이다. 그대로 둔다.
- `screen-01:1574/1577` · `screen-04:1598/1601` · `screen-06:1617/1620` · `screen-12:1657/1660` · `screen-17:1485/1488`. 이 **5파일에는 `.tabs` · `.tab` 마크업이 0건**이라 핸들러의 `querySelectorAll` 이 아무것도 잡지 못하는 죽은 셸 보일러플레이트다. 접근성에 영향이 없어 이번 라운드 교정 범위 밖이지만, React 이식 시 그대로 옮기면 안 되는 코드이므로 여기 기록해 둔다.

시각 결과는 무변경이다. 공용 CSS 가 `.tab.active` 클래스만 참조하고 `[aria-selected]` 같은 속성 선택자를 쓰지 않기 때문이다.

판정 근거. tabpanel 없는 tablist 는 스크린리더에 없는 패널을 약속하는 명백한 오류이고, `screen-11` 만 처음부터 그것을 회피했으며 판단 근거까지 문서화했다. 하나의 `Tabs` 로 뭉뚱그리면 지금의 접근성 오류가 코드로 굳는다. **실제 코드에는 같은 오용이 아직 남아 있다**(`frontend/src/app/(dashboard)/orders/_components/orders-blotter.tsx:125-134` `role="tablist"` + `role="tab"` + `aria-selected`, tabpanel 없음). 프로토타입 5화면이 보여 준 교정 형태를 그대로 옮기면 된다.

---

## 4. TypeScript 모듈 전문

### 4-0. 배치 판단 — 도메인별 분할 + 공용 원시 모듈 1개

**결론. `src/lib/labels.ts` 1개(톤 토큰 · 폴백 헬퍼 · 무데이터 표기)와 도메인별 `src/features/[domain]/labels.ts` 4개로 나눈다.**

근거 넷.

1. 프로젝트 구조 규약이 도메인 자산을 `features/[domain]/` 아래 두라고 정한다(`.ai/stacks/nextjs/frontend.md` §4 FSD Lite). 단일 전역 모듈은 이 규약의 예외를 새로 만든다.
2. enum 원본이 이미 `features/[domain]/schemas.ts` 에 있다. 라벨을 같은 폴더에 두면 `z.infer` 유니온과 `Record` 키가 한 파일 거리 안에 붙어, enum 추가 시 `Record` 누락이 즉시 타입 에러가 된다. `ONBOARDING_STEP_LABEL`(`frontend/src/features/onboarding/types.ts:15`)이 이미 그 형태다.
3. 단일 모듈이면 trading 화면이 optimizer enum 까지 import 하게 되어 도메인 경계가 무너진다. 지금 문제(`STATE_META` 가 라우트 폴더에 갇힘)의 반대 극단으로 넘어가는 것이지 해결이 아니다.
4. 다만 **톤 토큰과 폴백 규칙은 한 곳이어야 한다.** 그것이 갈리면 지금의 칩 톤 분기(§2-4)가 코드에서 재현된다. 그래서 `lib/labels.ts` 하나만 공용으로 둔다.

단일 모듈 안의 장점 하나는 "enum 당 한국어 1개" 를 grep 한 번으로 검증할 수 있다는 것이다. 그건 CI lint 규칙 한 줄(`features/**/labels.ts` 밖에서 상태 한국어 리터럴 금지)로 대체 가능하므로 구조를 희생할 이유가 못 된다.

### 4-1. `src/lib/labels.ts`

```ts
// 화면 표기 SSOT 의 공용 원시 타입 — 칩 톤 토큰, 무데이터 표기, 미지 enum 폴백 헬퍼.

/**
 * 상태 배지 톤. 프로토타입 셸 클래스와 1:1 대응한다.
 * - neutral: 아직 결과가 없거나 사용자 행위로 끝난 상태
 * - done   : 값이 남은 완결 상태 (--bull)
 * - accent : 진행 중이거나 활성인 상태 (--copper)
 * - warn   : 실패 · 거부 · 미저장 (--warn)
 */
export type ChipTone = "neutral" | "done" | "accent" | "warn";

/**
 * 톤에서 프로토타입 셸 클래스로의 매핑.
 * React 에서는 이 표만 디자인 토큰(data-tone 등)으로 갈아끼우면 되고,
 * 라벨 모듈은 손대지 않는다.
 */
export const CHIP_TONE_CLASS: Record<ChipTone, string> = {
  neutral: "chip",
  done: "chip done",
  accent: "chip accent",
  warn: "chip warn",
};

/**
 * 값 없음을 뜻하는 셀 표기 (U+2014).
 * 문자열 리터럴로 직접 쓰지 말고 이 상수를 참조한다.
 * 프로토타입 규약상 이 문자가 단독으로 쓰인 셀만 "데이터 없음" 관례로 허용된다.
 */
export const EMPTY_CELL = "—";

/** 라벨 1개와 톤 1개. 상태 계열 enum 이 공통으로 쓰는 모양. */
export interface StatusLabel {
  readonly label: string;
  readonly tone: ChipTone;
}

/** 체크 아이콘을 붙이는 톤인지. done 이면서 완결 실행·주문일 때만 true 를 넘긴다. */
export interface StatusLabelWithIcon extends StatusLabel {
  readonly showCheckIcon?: boolean;
}

function warnUnknownKey(key: string, scope: string): void {
  if (process.env.NODE_ENV !== "production") {
    // 서버가 새 enum 을 먼저 배포한 경우를 개발 중에 즉시 드러낸다.
    console.warn(`[labels] ${scope} 에 없는 enum 값입니다: ${key}`);
  }
}

/**
 * 미지 enum 폴백 (문자열 라벨).
 * 표에 없는 값이 오면 원문을 그대로 돌려준다. 화면이 빈칸이 되거나
 * undefined 접근으로 터지는 것보다 낫고, 원시 enum 노출 자체가 버그 신호다.
 */
export function labelOf<K extends string>(
  table: Readonly<Record<K, string>>,
  key: string,
  scope = "labels",
): string {
  const hit = (table as Readonly<Record<string, string | undefined>>)[key];
  if (hit === undefined) {
    warnUnknownKey(key, scope);
    return key;
  }
  return hit;
}

/**
 * 미지 enum 폴백 (라벨 + 톤).
 * 톤은 중립으로 떨어뜨린다. 모르는 상태를 성공·실패 색으로 칠하지 않기 위해서다.
 */
export function statusLabelOf<K extends string>(
  table: Readonly<Record<K, StatusLabelWithIcon>>,
  key: string,
  scope = "labels",
): StatusLabelWithIcon {
  const hit = (
    table as Readonly<Record<string, StatusLabelWithIcon | undefined>>
  )[key];
  if (hit === undefined) {
    warnUnknownKey(key, scope);
    return { label: key, tone: "neutral" };
  }
  return hit;
}

/** 값이 null 또는 undefined 면 무데이터 표기로 바꾼다. */
export function orEmptyCell(value: string | number | null | undefined): string {
  return value === null || value === undefined ? EMPTY_CELL : String(value);
}
```

### 4-2. `src/features/trading/labels.ts`

```ts
// 트레이딩 도메인 화면 표기 SSOT — 주문 상태·주문 방향·포지션 방향·실행 경로·표 헤더.
// 프로토타입 원장은 screen-11-orders.html(주문) 과 screen-01-trading-cockpit.html(포지션) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type { Order } from "./schemas";

export type OrderState = Order["state"];
export type OrderSide = Order["side"];

/** 주문 상태 5종. screen-11-orders.html:1290/1304/1346/1360/1374 */
export const ORDER_STATE_LABEL: Record<OrderState, StatusLabelWithIcon> = {
  pending: { label: "대기", tone: "neutral" },
  submitted: { label: "전송", tone: "neutral" },
  filled: { label: "체결", tone: "done", showCheckIcon: true },
  cancelled: { label: "취소", tone: "neutral" },
  rejected: { label: "거부", tone: "warn" },
};

/**
 * 주문 방향. 포지션의 롱·숏과는 다른 값이라 배지 클래스도 분리한다
 * (.order-side.buy/.sell vs .side.long/.short). screen-11-orders.html:1271
 */
export const ORDER_SIDE_LABEL: Record<OrderSide, string> = {
  buy: "매수",
  sell: "매도",
};

/** 포지션 방향. screen-01-trading-cockpit.html:1238 · screen-04-trade-detail.html:1265 */
export type PositionSide = "long" | "short";
export const POSITION_SIDE_LABEL: Record<PositionSide, string> = {
  long: "롱",
  short: "숏",
};

/**
 * 실행 경로 3단. 서로 직교하는 축이므로 하나로 합치지 않는다.
 * mock = 로컬 목 어댑터 / demo = Bybit 데모 계정 / live = 실자금.
 */
export type ExecutionMode = "mock" | "demo" | "live";
export const EXECUTION_MODE_LABEL: Record<ExecutionMode, string> = {
  mock: "모의",
  demo: "데모",
  live: "라이브",
};
/** screen-11-orders.html:1404 title · screen-01-trading-cockpit.html:1553 · screen-16-pricing.html:1487 */
export const EXECUTION_MODE_HINT: Record<ExecutionMode, string> = {
  mock: "거래소를 붙이지 않고 로컬 목 어댑터로 실행한 주문입니다. 실제 거래소에는 나가지 않았습니다.",
  demo: "데모는 실거래와 같은 코드 경로를 쓰지만 슬리피지와 체결 지연은 다르게 나타납니다.",
  live: "라이브 주문은 실제 자금을 움직이고 손실은 사용자 책임입니다.",
};

/** 주문번호 출처 배지. screen-11-orders.html:1306(브로커) · :1404(모의) */
export type OrderIdSource = "broker" | "mock";
export const ORDER_ID_SOURCE_LABEL: Record<OrderIdSource, string> = {
  broker: "브로커",
  mock: "모의",
};

/**
 * 주문 표 헤더 10열. screen-11-orders.html:1269-1278 의 th 를 순서대로 옮긴 것이고
 * 문자열은 화면이 인쇄하는 값과 바이트 일치한다.
 * 주의 둘. createdAt 은 "시간" 이 아니라 "시각" 이다.
 * takeProfitStopLoss 는 가운뎃점 앞뒤에 공백이 없다("익절·손절").
 */
export const ORDER_TABLE_HEADER = {
  createdAt: "시각",
  symbol: "심볼",
  side: "주문 방향",
  quantity: "수량",
  filledPrice: "체결가",
  state: "상태",
  takeProfitStopLoss: "익절·손절",
  brokerOrderId: "거래소 주문번호",
  errorMessage: "오류",
  action: "액션",
} as const;

/** 주문 방향 열 헤더 title. 롱·숏과의 혼동을 막는 문구다. */
export const ORDER_SIDE_HEADER_HINT =
  "주문의 매수·매도 방향입니다. 포지션의 롱·숏 방향과는 다른 값이라 트레이딩 코크핏의 롱·숏 배지와 구분해 표시합니다.";

/** 부가 플래그 배지. screen-11-orders.html:1287 */
export const ORDER_FLAG_LABEL = {
  reduceOnly: "감소전용",
} as const;
export const ORDER_FLAG_HINT = {
  reduceOnly:
    "열려 있는 포지션을 줄이는 주문입니다. 새 포지션을 만들지 않습니다.",
} as const;

/**
 * 상태 필터 탭. 라벨 단위(5종)와 필터 단위(4종)의 입도가 다르다.
 * 화면은 라벨 뒤에 건수를 붙여 인쇄한다(전체 14 / 체결 5 / 대기·전송 7 / 취소·거부 2).
 * 건수는 데이터에서 파생되므로 라벨만 여기 둔다. screen-11-orders.html:1219-1222
 */
export type OrderStateFilter = "all" | "filled" | "open" | "closed";
export const ORDER_STATE_FILTER_LABEL: Record<OrderStateFilter, string> = {
  all: "전체",
  filled: "체결",
  open: "대기·전송",
  closed: "취소·거부",
};

/** 무데이터 사유. screen-11-orders.html:1289 · :1292 · :1347 · :1348 */
export const ORDER_EMPTY_REASON = {
  filledPriceNotYet: "아직 체결되지 않아 체결가가 없습니다.",
  brokerIdNotSent: "아직 거래소로 보내지 않아 주문번호가 없습니다.",
  brokerIdRejected: "거래소로 나가기 전에 걸러져서 주문번호가 없습니다.",
  takeProfitStopLossRejected:
    "거래소로 나가기 전에 걸러져서 익절과 손절도 붙지 않았습니다.",
} as const;

/**
 * 청산가는 주문 표에 두지 않는다. 체결된 주문이 곧 열린 포지션을 뜻하지 않고
 * 포지션 API 도 없기 때문이다. 포지션 화면으로 위임한다.
 * 원문 4문장 그대로다. screen-11-orders.html:1479
 */
export const ORDER_LIQUIDATION_DELEGATION_NOTE =
  "청산가는 이 표에 표시하지 않습니다. 체결된 주문이 곧 열린 포지션을 뜻하지 않고(이미 청산됐을 수 있습니다), 지금 포지션을 돌려주는 API 도 아직 없기 때문입니다. 확인할 수 없는 값을 라이브 위험처럼 보이게 하지 않으려고 칸 자체를 두지 않았습니다. 포지션은 트레이딩 코크핏에서 확인하세요.";

/** 킬 스위치. 기능명과 버튼 라벨(동사형)을 분리한다. screen-01-trading-cockpit.html:1336 · :1154 · :1157 */
export const KILL_SWITCH_LABEL = {
  feature: "킬 스위치",
  action: "긴급 정지",
  confirm:
    "긴급 정지는 모든 포지션 시장가 청산 후 세션 중지. 되돌릴 수 없습니다.",
} as const;

/** 세션 빈 상태. screen-11-orders.html:1572-1573 (카드 제목 :1563 "라이브 세션 주문") */
export const ORDER_EMPTY_STATE = {
  headline: "표시할 주문이 없습니다.",
  description: "라이브·데모 세션이 주문을 실행하면 이곳 원장에 기록됩니다.",
} as const;
```

### 4-3. `src/features/optimizer/labels.ts`

```ts
// 옵티마이저 도메인 화면 표기 SSOT — 방식·상태·목표 지표·방향·파라미터 필드·표 헤더.
// 프로토타입 원장은 screen-09-optimizer-list.html(목록) 과 screen-10-optimizer-detail.html(상세) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type {
  BayesianPrior,
  OptimizationDirection,
  OptimizationKind,
  OptimizationObjectiveMetric,
  OptimizationStatus,
} from "./schemas";

/**
 * 도메인명은 역할로 나뉜다.
 * page   = 사이드바 · title · breadcrumb · h1 · 푸터 5축 (screen-09-optimizer-list.html:1563)
 * action = 동사 · 실행 유형 (screen-09-optimizer-list.html:1179 "최적화 제출")
 */
export const OPTIMIZER_DOMAIN_LABEL = {
  page: "옵티마이저",
  action: "최적화",
} as const;

/** 방식 3종. screen-09-optimizer-list.html:1200-1202 셀렉트 옵션 */
export const OPTIMIZATION_KIND_LABEL: Record<OptimizationKind, string> = {
  grid_search: "그리드 탐색",
  bayesian: "베이지안 탐색",
  genetic: "유전 알고리즘",
};

/** 실행 상태 4종. screen-09-optimizer-list.html:1296/1310/1323/1346 */
export const OPTIMIZATION_STATUS_LABEL: Record<
  OptimizationStatus,
  StatusLabelWithIcon
> = {
  queued: { label: "대기", tone: "neutral" },
  running: { label: "실행 중", tone: "accent" },
  completed: { label: "완료", tone: "done", showCheckIcon: true },
  failed: { label: "실패", tone: "warn" },
};

/** 목표 지표 3종 완전형. screen-09-optimizer-list.html:1209-1211 셀렉트 옵션 */
export const OBJECTIVE_METRIC_LABEL: Record<
  OptimizationObjectiveMetric,
  string
> = {
  sharpe_ratio: "샤프 지수",
  total_return: "총 수익률",
  max_drawdown: "최대 낙폭",
};

/**
 * 표 헤더용 축약. 시각 텍스트는 완전형을 쓰고 이 값은 th 의 abbr 속성에만 넣는다.
 * 정답 형태는 screen-02-dashboard.html:1304 의 <th abbr="MDD">최대 낙폭</th> 이다.
 */
export const OBJECTIVE_METRIC_ABBR: Record<
  OptimizationObjectiveMetric,
  string
> = {
  sharpe_ratio: "샤프",
  total_return: "수익률",
  max_drawdown: "MDD",
};

/** 최적화 방향. screen-09-optimizer-list.html:1218-1219 */
export const OBJECTIVE_DIRECTION_LABEL: Record<OptimizationDirection, string> =
  {
    maximize: "최대화",
    minimize: "최소화",
  };
export const OBJECTIVE_DIRECTION_HINT: Record<OptimizationDirection, string> = {
  maximize: "큰 값이 좋음",
  minimize: "작은 값이 좋음",
};

/**
 * 파라미터 공간 필드 종류. 원시 kind 문자열을 그대로 인쇄하지 않는다.
 * **프로토타입 미측정 · 확장분.** 네 라벨 모두 17벌에 0건이며 코드 노출을 막기 위해 새로 지었다.
 */
export type ParamFieldKind = "integer" | "decimal" | "categorical" | "bayesian";
export const PARAM_FIELD_KIND_LABEL: Record<ParamFieldKind, string> = {
  integer: "정수 구간",
  decimal: "실수 구간",
  categorical: "범주 목록",
  bayesian: "연속 구간",
};

/** 베이지안 사전분포. **프로토타입 미측정 · 확장분** (세 라벨 모두 17벌에 0건). */
export const BAYESIAN_PRIOR_LABEL: Record<BayesianPrior, string> = {
  uniform: "균등",
  log_uniform: "로그 균등",
  normal: "정규",
};

/** 베이지안 반복 단계. screen-10 에는 인쇄되지 않았고 코드 노출을 막기 위한 확장분이다. */
export type BayesianPhase = "random" | "acquisition";
export const BAYESIAN_PHASE_LABEL: Record<BayesianPhase, string> = {
  random: "초기 랜덤",
  acquisition: "획득 함수",
};

/** 실행 목록 표 헤더 8열. screen-09-optimizer-list.html:1277-1284 · 화면 문자열과 바이트 일치 */
export const OPTIMIZER_LIST_HEADER = {
  runId: "실행 ID",
  kind: "방식",
  backtest: "대상 백테스트",
  objective: "목표 지표",
  bestObjective: "최고 목표값",
  status: "상태",
  createdAt: "생성 시각",
  action: "액션",
} as const;

/**
 * 셀 리더보드 표 헤더 8열. screen-10-optimizer-detail.html:1320-1327.
 * 주의 셋. 첫 열은 "순위" 가 아니라 "표시 순서" 다. 정렬을 바꿔도 목표 함수와
 * "최적" 표시는 고정이라는 사실(:1427)과 맞추려고 화면이 고른 말이다.
 * 파라미터는 단일 "파라미터" 열이 아니라 fastLength · slowLength 2열로 분리돼 있다.
 * 목표값 전용 열은 없다. 목표 함수인 샤프 지수 열이 그 역할을 겸한다.
 * 이 표는 이 실행의 파라미터 이름을 그대로 인쇄하므로 열 구성이 실행마다 달라진다.
 * 그래서 아래 두 키는 이 프로토타입 실행(MA Crossover 그리드 탐색)의 실측값이고,
 * 이식할 때는 param_space 의 필드 이름에서 만들어야 한다.
 */
export const OPTIMIZER_CELL_HEADER = {
  displayOrder: "표시 순서",
  paramFast: "fastLength",
  paramSlow: "slowLength",
  sharpe: "샤프 지수",
  totalReturn: "총 수익률",
  maxDrawdown: "최대 낙폭",
  numTrades: "거래 수",
  action: "액션",
} as const;

/**
 * 무데이터 사유. 상태별로 문구가 다르다.
 * screen-09-optimizer-list.html:1297 / :1308 / :1344 · screen-10-optimizer-detail.html:1415 / :1412
 */
export const OPTIMIZER_EMPTY_REASON = {
  queuedNotStarted: "아직 실행이 시작되지 않아 평가 결과가 없습니다.",
  queuedNoQueuePosition:
    "시작 시각이 아직 없습니다. 대기열 순번은 서버가 보고하지 않습니다.",
  runningNoIntermediate:
    "실행이 끝나야 결과가 저장됩니다. 서버는 중간 최고값을 보고하지 않습니다.",
  failedInvalidRange:
    "파라미터 공간의 하한이 상한보다 커서 탐색 범위를 만들지 못했고, 평가가 한 번도 실행되지 않았습니다.",
  degenerateNoSharpe: "거래가 0건이라 샤프 지수를 계산할 표본이 없습니다.",
  degenerateNoRank: "거래가 0건이라 순위를 매길 근거가 없습니다.",
  noEtaByDesign:
    "실행 중 작업의 남은 시간은 표시하지 않습니다. 서버가 진행 회차를 아직 보고하지 않기 때문입니다.",
  noProgressMeter:
    "최적화는 서버가 진행률을 보고하지 않아 미터를 그리지 않습니다.",
} as const;

/**
 * 빈 상태. screen-09 가 실제로 그리는 빈 상태는 "실행 이력 없음" 이 아니라
 * "보관함 비어 있음" 하나뿐이다. screen-09-optimizer-list.html:1484-1485
 */
export const OPTIMIZER_ARCHIVE_EMPTY_STATE = {
  headline: "보관한 실행이 없습니다.",
  description:
    "끝난 실행을 보관해 두면 목록에서 빠지고, 결과는 그대로 남습니다.",
} as const;

/** 목록 로드 실패. screen-09-optimizer-list.html:1460-1461 */
export const OPTIMIZER_LIST_ERROR_STATE = {
  headline: "목록을 다시 불러오지 못했습니다.",
  description:
    "위 표는 마지막으로 성공한 응답입니다. 그 뒤로 갱신되지 않았습니다.",
} as const;

/** 대상 백테스트 선택 제약. screen-09-optimizer-list.html:1235 · 원문 3문장 그대로다 */
export const OPTIMIZER_BACKTEST_PICKER_NOTE =
  "목록에는 완료된 백테스트만 나옵니다. 실행 중이거나 실패한 백테스트는 최적화의 기준이 될 수 없습니다. 최대 낙폭을 목표로 고르면 방향은 최소화가 기본값입니다.";

/** 방식별 상한. screen-09-optimizer-list.html:1231 · 원문 2문장 그대로다 */
export const OPTIMIZER_LIMIT_NOTE =
  "지금 고른 그리드 탐색은 조합 수가 9개를 넘으면 제출이 거부됩니다. 베이지안 탐색과 유전 알고리즘은 조합 대신 평가 횟수로 끊으며 상한은 100회입니다.";
```

> **`OPTIMIZER_EMPTY_STATE` 삭제 기록 (2026-07-20).** 이전 판본은 `아직 최적화 실행이 없습니다.` / `완료된 백테스트를 고르고 최적화를 제출하면 이곳에 기록됩니다.` 를 실행 이력 빈 상태로 실었으나 **두 문자열 모두 17벌에 0건**이다. 추정으로 채운 값이라 삭제하고, 화면이 실제로 그리는 빈 상태 두 종(보관함 · 로드 실패)으로 교체했다. §5-3 의 `optimizer-run-list.tsx:52·58` 교체 대상도 함께 고쳤다.

### 4-4. `src/features/backtest/labels.ts`

```ts
// 백테스트 도메인 화면 표기 SSOT — 실행 상태·거래 방향·지표 이름·표 헤더.
// 프로토타입 원장은 screen-03-backtests-list.html(실행 원장) 과 screen-04-trade-detail.html(거래) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type { BacktestStatus, TradeDirection, TradeStatus } from "./schemas";

/**
 * 실행 상태. queued/running/completed/failed 4종은 프로토타입 실측값이고
 * cancelling/cancelled 2종은 화면에 없어 코드 enum 을 덮기 위한 확장분이다.
 * screen-03-backtests-list.html:1215-1221 (aria-label="상태 필터" 셀렉트,
 * 옵션 5개 = 상태 전체 + 완료 + 실행 중 + 실패 + 대기)
 */
export const BACKTEST_STATUS_LABEL: Record<
  BacktestStatus,
  StatusLabelWithIcon
> = {
  queued: { label: "대기", tone: "neutral" },
  running: { label: "실행 중", tone: "accent" },
  completed: { label: "완료", tone: "done", showCheckIcon: true },
  failed: { label: "실패", tone: "warn" },
  cancelling: { label: "취소 중", tone: "neutral" }, // 프로토타입 미측정 · 확장분
  cancelled: { label: "취소", tone: "neutral" }, // 프로토타입 미측정 · 확장분
};

/** 상태 필터 탭. 라벨은 배지와 같은 문자열을 쓴다. */
export type BacktestStatusFilter = "all" | BacktestStatus;
export const BACKTEST_STATUS_FILTER_LABEL: Record<
  BacktestStatusFilter,
  string
> = {
  all: "전체",
  queued: "대기",
  running: "실행 중",
  cancelling: "취소 중",
  completed: "완료",
  failed: "실패",
  cancelled: "취소",
};

/** 거래 방향. screen-04-trade-detail.html:1234-1235 */
export const TRADE_DIRECTION_LABEL: Record<TradeDirection, string> = {
  long: "롱",
  short: "숏",
};

/** 거래 상태. 프로토타입 미측정 · 확장분 ("보유 중" 만 screen-01 에 있고 "청산됨" 은 17벌 0건). */
export const TRADE_STATUS_LABEL: Record<TradeStatus, string> = {
  open: "보유 중",
  closed: "청산됨",
};

/**
 * 성과 지표 이름. 완전형만 화면 텍스트로 쓰고 축약은 th 의 abbr 속성에만 넣는다.
 * total_return 계열 3종은 서로 다른 enum 이므로 합치지 않는다.
 */
export const METRIC_LABEL = {
  totalReturn: "총 수익률",
  maxDrawdown: "최대 낙폭",
  sharpeRatio: "샤프 지수",
  sortinoRatio: "소르티노 지수", // 프로토타입 미측정 · 확장분 (17벌 0건)
  calmarRatio: "칼마 지수", // 프로토타입 미측정 · 확장분 (17벌 0건)
  winRate: "승률", // screen-04-trade-detail.html · screen-12-onboarding.html
  profitLossRatio: "손익비", // screen-04-trade-detail.html
  profitFactor: "수익 팩터", // screen-04-trade-detail.html
  numTrades: "거래 수",
  avgHoldingTime: "평균 보유", // screen-04-trade-detail.html
  /** 미결제 포지션의 진입가 대비 등락률. screen-01-trading-cockpit.html:1228 */
  positionUnrealizedReturn: "수익률",
  /** 거래 1건의 비용 차감 후 수익률. screen-04-trade-detail.html:1407 · 검산 :1411 */
  tradeRealizedReturn: "실현 수익률",
  /** 거래 1건의 비용 제외 총변동률. screen-04-trade-detail.html:1258 */
  tradeGrossReturn: "변동률",
  /** 전략의 가장 최근 완료 백테스트 1건 기준 수익률. screen-06-strategies-list.html:1246 */
  strategyLastRunReturn: "최근 수익률",
} as const;

export const METRIC_ABBR = {
  totalReturn: "수익률",
  maxDrawdown: "MDD",
  sharpeRatio: "샤프",
} as const;

/**
 * 실행 목록 표 헤더 11열. screen-03-backtests-list.html:1291-1326.
 * 주의 넷. 심볼과 주기는 별도 열이 아니라 "심볼 · 주기" 단일 th 다(:1293).
 * 시각 열 이름은 "생성 시각" 이 아니라 "실행 시각" 이다(:1320-1325).
 * 수익률·MDD·샤프 3열은 정렬 button 안의 시각 텍스트가 축약형이고
 * 완전형은 button 의 aria-label 에 있다. 두 값을 따로 들고 간다.
 * 액션 열이 있다(:1326).
 */
export const BACKTEST_LIST_HEADER = {
  runId: "실행 ID",
  strategy: "전략",
  symbolTimeframe: "심볼 · 주기",
  period: "기간",
  totalReturn: "수익률",
  maxDrawdown: "MDD",
  sharpeRatio: "샤프",
  numTrades: "거래 수",
  status: "상태",
  startedAt: "실행 시각",
  action: "액션",
} as const;

/**
 * 정렬 button 의 접근성 이름. 시각 텍스트가 축약형인 열만 갖는다.
 * screen-03-backtests-list.html:1296 / :1302 / :1308 / :1314 / :1321
 */
export const BACKTEST_LIST_SORT_LABEL = {
  totalReturn: "수익률 기준 정렬",
  maxDrawdown: "최대 낙폭 기준 정렬",
  sharpeRatio: "샤프 지수 기준 정렬",
  numTrades: "거래 수 기준 정렬",
  startedAt: "실행 시각 기준 정렬, 현재 내림차순으로 최근 실행이 위에 옵니다",
} as const;

/** 무데이터 사유. screen-03-backtests-list.html:1350 / :1357 / :1369 / :1417 / :1424 */
export const BACKTEST_EMPTY_REASON = {
  queuedNotStarted: "아직 실행이 시작되지 않았습니다.",
  queuedNoQueuePosition:
    "시작 시각이 아직 없습니다. 대기열 순번은 서버가 보고하지 않습니다.",
  runningNotFinished: "실행이 끝나야 계산됩니다.",
  failedDataCollection:
    "Bybit OHLCV 수집이 중단되어 실행이 완료되지 않았습니다.",
  failedStageNote: "데이터 수집 단계에서 중단",
} as const;

/** 신규 실행 화면명. 진입 버튼 라벨이 정본이고 h1 만 동사형을 유지한다. */
export const NEW_BACKTEST_LABEL = {
  entry: "새 백테스트",
  heading: "새 백테스트 실행",
} as const;
```

### 4-5. `src/features/strategy/labels.ts`

```ts
// 전략 도메인 화면 표기 SSOT — Pine 파싱 상태·전략 수명주기 상태·정책 문구.
// 프로토타입 원장은 screen-06-strategies-list.html(목록 12행) 이다.

import type { StatusLabelWithIcon } from "@/lib/labels";
import type { ParsePreviewResponse } from "./schemas";

export type ParseStatus = ParsePreviewResponse["status"];

/**
 * Pine 파싱 미리보기 결과. 지금 코드에는 같은 Record 가 두 파일에 복제돼 있고
 * ok 값이 "변환 완료"(new) 와 "변환 가능"(edit) 으로 갈렸다.
 * 미리보기 단계에서는 아직 아무것도 변환되지 않았으므로 "변환 가능" 이 정확하다.
 * **근거는 실 코드이고 프로토타입 근거는 없다.** 세 라벨 모두 17벌에 0건이므로
 * 이 Record 만은 화면 실측이 아니라 코드 간 중복 해소 판정이다.
 */
export const PARSE_STATUS_LABEL: Record<ParseStatus, StatusLabelWithIcon> = {
  ok: { label: "변환 가능", tone: "done", showCheckIcon: true },
  unsupported: { label: "일부 미지원", tone: "warn" },
  error: { label: "오류", tone: "warn" },
};

/**
 * 전략 수명주기 상태.
 * 주의. 이 enum 은 현재 백엔드·프론트 스키마에 존재하지 않고 프로토타입 캐논에만 있다
 * (frontend/src/features/strategy/schemas.ts 에 대응 필드 0건).
 * 서버가 필드를 내려주기 전까지는 이 Record 를 화면에 연결하지 않는다.
 * screen-06-strategies-list.html:1260(배포됨) · :1281(검증됨) · :1302(초안)
 */
export type StrategyLifecycle = "draft" | "validated" | "deployed";
export const STRATEGY_LIFECYCLE_LABEL: Record<
  StrategyLifecycle,
  StatusLabelWithIcon
> = {
  draft: { label: "초안", tone: "neutral" },
  validated: { label: "검증됨", tone: "done" }, // 체크 아이콘 없음 (screen-06 6건 전부)
  deployed: { label: "배포됨", tone: "accent" },
};

/**
 * 전략 목록 표 헤더 10열. screen-06-strategies-list.html:1242-1251.
 * 주의 넷. 첫 열은 "전략" 이 아니라 "전략명" 이다.
 * 심볼과 주기는 별도 열이 아니라 "심볼 · 주기" 단일 th 다(:1244).
 * MDD·샤프 2열은 시각 텍스트가 축약형이고 완전형은 th 의 aria-label 에 있다.
 * 상태 열(:1243)과 액션 열(:1251)이 있다.
 */
export const STRATEGY_LIST_HEADER = {
  name: "전략명",
  status: "상태",
  symbolTimeframe: "심볼 · 주기",
  paramCount: "파라미터",
  lastRunReturn: "최근 수익률",
  maxDrawdown: "MDD",
  sharpeRatio: "샤프",
  backtestCount: "백테스트",
  updatedAt: "마지막 수정",
  action: "액션",
} as const;

/**
 * 축약 th 의 접근 가능한 이름. screen-06 은 정렬 컨트롤이 없는 정적 th 라
 * screen-03 처럼 "... 기준 정렬" 을 쓰지 않고 확정 용어만 넣는다.
 * screen-06-strategies-list.html:1247 · :1248
 */
export const STRATEGY_LIST_HEADER_ARIA = {
  maxDrawdown: "최대 낙폭",
  sharpeRatio: "샤프 지수",
} as const;

/**
 * 백테스트 카운트 열의 정의를 반드시 명시한다.
 * 화면이 열 이름을 "백테스트" 로만 인쇄해 완료 기준인지 전체 실행 기준인지
 * 프로토타입만으로는 확정할 수 없었다 (screen-06-strategies-list.html:1249).
 */
export const STRATEGY_BACKTEST_COUNT_HINT =
  "완료된 백테스트 수입니다. 실행 중이거나 실패한 실행은 세지 않습니다.";

/** 무데이터 사유. screen-06-strategies-list.html:1305-1307 (06 에서 4행 x 3칸 = 12셀) */
export const STRATEGY_EMPTY_REASON = {
  noBacktestYet: "아직 백테스트를 실행하지 않았습니다.",
} as const;

/** ADR-003 전체 미지원 정책. 화면마다 갈린 어휘를 하나로 잠근다. */
export const UNSUPPORTED_POLICY_NOTE =
  "미지원 함수가 하나라도 있으면 부분 실행 없이 전체를 지원되지 않음으로 처리합니다. 잘못된 결과를 내는 것보다 낫습니다.";

/** 엔진 표기. ADR-011 상 "벡터화" 표기는 금지다. */
export const ENGINE_LABEL = "pine_v2 · 바 단위 이벤트 루프";
```

---

## 5. 적용 지점 목록

**이 문서는 코드를 수정하지 않는다.** 아래는 이식 승인 시 교체할 위치와 현재 상태의 실측 근거다.

### 5-1. `frontend/src/features/trading/components/orders-panel.tsx`

| 줄              | 현재 인쇄값                                                     | 교체 대상                                                                                  |
| --------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 97              | `<th>Symbol</th>`                                               | `ORDER_TABLE_HEADER.symbol` = 심볼                                                         |
| 98              | `<th>Side</th>`                                                 | `ORDER_TABLE_HEADER.side` = 주문 방향 (+ `ORDER_SIDE_HEADER_HINT` title)                   |
| 99              | `<th>Qty</th>`                                                  | `ORDER_TABLE_HEADER.quantity` = 수량                                                       |
| 100             | `<th>State</th>`                                                | `ORDER_TABLE_HEADER.state` = 상태                                                          |
| 101             | `<th>Price</th>`                                                | `ORDER_TABLE_HEADER.filledPrice` = 체결가                                                  |
| 103             | `<th>TP/SL</th>`                                                | `ORDER_TABLE_HEADER.takeProfitStopLoss` = 익절·손절 (가운뎃점 앞뒤 공백 없음)              |
| 104             | `<th>청산가</th>`                                               | **열 제거.** `ORDER_LIQUIDATION_DELEGATION_NOTE` 로 위임 (screen-11-orders.html:1479 판정) |
| 105             | `<th>Broker ID</th>`                                            | `ORDER_TABLE_HEADER.brokerOrderId` = 거래소 주문번호                                       |
| 106             | `<th>Error</th>`                                                | `ORDER_TABLE_HEADER.errorMessage` = 오류                                                   |
| 113             | `{o.side}` 원시 enum(`buy`/`sell`)                              | `ORDER_SIDE_LABEL[o.side]`                                                                 |
| 115             | `{o.state}` 원시 enum(5종)                                      | `statusLabelOf(ORDER_STATE_LABEL, o.state)` + 칩 톤                                        |
| 116 · 124 · 135 | `"—"` 문자열 리터럴 3곳                                         | `EMPTY_CELL`                                                                               |
| 19-44           | `BrokerBadge` 가 영문 `(mock)` `(broker)` 를 인쇄 (`:31` `:41`) | `ORDER_ID_SOURCE_LABEL` + `EXECUTION_MODE_HINT.mock`                                       |
| 131-136         | 청산가 셀이 항상 무데이터를 렌더                                | 열 삭제 시 함께 제거                                                                       |

9개 헤더 중 7개가 영문이다. 청산가 열은 프로토타입 원장이 의도적으로 제거한 열이므로 번역이 아니라 삭제 대상이다.

### 5-2. `frontend/src/app/(dashboard)/orders/_components/orders-blotter.tsx`

| 줄       | 현재 상태                                                                | 조치                                                         |
| -------- | ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| 33-42    | `STATE_META` Record 가 라우트 폴더에 갇혀 있음. 라벨은 프로토타입과 일치 | `features/trading/labels.ts` 로 이동. 이 파일은 import 만    |
| 19-24    | `STATE_TABS` 라벨 4종                                                    | `ORDER_STATE_FILTER_LABEL`                                   |
| 58       | CSV 헤더 `["시간","심볼","방향","수량","체결가","상태"]`                 | `ORDER_TABLE_HEADER` (시간 -> 시각, 방향 -> 주문 방향)       |
| 62 · 217 | `o.side === "buy" ? "매수" : "매도"` 삼항이 2곳 중복                     | `ORDER_SIDE_LABEL[o.side]`                                   |
| 192-197  | th 6개 한국어. `방향` 만 `주문 방향` 으로 교정 필요                      | `ORDER_TABLE_HEADER`                                         |
| 220-222  | `감소전용` 문자열 리터럴 (title 없음)                                    | `ORDER_FLAG_LABEL.reduceOnly` + `ORDER_FLAG_HINT.reduceOnly` |
| 229      | `"—"` 리터럴                                                             | `EMPTY_CELL`                                                 |
| 125-134  | `role="tablist"` + `role="tab"` + `aria-selected` 인데 tabpanel 이 없음  | §3-6 오용. `role="group"` + `aria-pressed` 로 교정           |
| 65       | `STATE_META[o.state].label` 이 미지 값에서 터진다                        | `statusLabelOf` 폴백                                         |
| 183      | 빈 상태 문구가 프로토타입과 일치 (`screen-11-orders.html:1573`)          | `ORDER_EMPTY_STATE.description` 로 승격                      |

### 5-3. `frontend/src/app/(dashboard)/optimizer/_components/optimizer-run-list.tsx`

| 줄      | 현재 인쇄값                                                                  | 교체 대상                                                                                                                                                                                                                      |
| ------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 78      | `<th>ID</th>`                                                                | `OPTIMIZER_LIST_HEADER.runId` = 실행 ID                                                                                                                                                                                        |
| 79      | `<th>Status</th>`                                                            | `OPTIMIZER_LIST_HEADER.status` = 상태                                                                                                                                                                                          |
| 80      | `<th>Objective</th>`                                                         | `OPTIMIZER_LIST_HEADER.objective` = 목표 지표                                                                                                                                                                                  |
| 81      | `<th>Best</th>`                                                              | `OPTIMIZER_LIST_HEADER.bestObjective` = 최고 목표값                                                                                                                                                                            |
| 82      | `<th>Created</th>`                                                           | `OPTIMIZER_LIST_HEADER.createdAt` = 생성 시각                                                                                                                                                                                  |
| 117     | `{r.status}` 원시 enum(`queued`/`running`/`completed`/`failed`)              | `statusLabelOf(OPTIMIZATION_STATUS_LABEL, r.status)`                                                                                                                                                                           |
| 121     | `{r.param_space.objective_metric} ({r.param_space.direction})` 원시 enum 2개 | `OBJECTIVE_METRIC_LABEL` + `OBJECTIVE_DIRECTION_LABEL`                                                                                                                                                                         |
| 11-19   | `STATUS_BADGE` 가 톤을 `success`/`destructive`/클래스로 3갈래 표현           | `ChipTone` 4종으로 통일. `running` 은 accent                                                                                                                                                                                   |
| 124     | `"—"` 리터럴                                                                 | `EMPTY_CELL`                                                                                                                                                                                                                   |
| 42      | `Optimizer 목록을 불러오지 못했습니다.` 영문 도메인명                        | `OPTIMIZER_DOMAIN_LABEL.page` = 옵티마이저                                                                                                                                                                                     |
| 52 · 58 | `Optimizer 실행 이력 없음. 새 Grid Search 를 제출하세요.` 영문 2개           | **프로토타입에 대응 문구가 없다.** `screen-09` 가 그리는 빈 상태는 보관함(`OPTIMIZER_ARCHIVE_EMPTY_STATE`)과 로드 실패(`OPTIMIZER_LIST_ERROR_STATE`) 둘뿐이다. 실행 이력 빈 상태 카피는 새로 정해야 하므로 §6 에 미결로 올린다 |

5개 헤더 전부 영문이고 원시 enum 노출이 3종이다.

### 5-4. `frontend/src/app/(dashboard)/optimizer/_components/optimizer-run-detail.tsx`

| 줄                          | 현재 인쇄값                                                                                         | 교체 대상                                                                                                                                    |
| --------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 42                          | `상태 <strong>{data.status}</strong>` 원시 enum                                                     | `OPTIMIZATION_STATUS_LABEL`                                                                                                                  |
| 45                          | `방식 {data.kind}` 원시 enum(`grid_search` 등)                                                      | `OPTIMIZATION_KIND_LABEL`                                                                                                                    |
| 48                          | `목표 지표 {objective_metric} ({direction})` 원시 enum 2개                                          | `OBJECTIVE_METRIC_LABEL` + `OBJECTIVE_DIRECTION_LABEL`                                                                                       |
| 67-76                       | `field.kind` 를 `integer` `decimal` `bayesian` `categorical` 원시 문자열로 인쇄. `prior=` 도 원시값 | `PARAM_FIELD_KIND_LABEL` + `BAYESIAN_PRIOR_LABEL`                                                                                            |
| 117                         | `({data.result.objective_metric} = ...)` 원시 enum                                                  | `OBJECTIVE_METRIC_LABEL`                                                                                                                     |
| 202                         | `<td>{it.phase}</td>` 원시 enum(`random`/`acquisition`)                                             | `BAYESIAN_PHASE_LABEL`                                                                                                                       |
| 136-139                     | th `샤프` `수익률` `최대낙폭` 축약형 3개                                                            | `OPTIMIZER_CELL_HEADER` 완전형(`샤프 지수` / `총 수익률` / `최대 낙폭`). screen-10 리더보드는 축약을 쓰지 않으므로 `abbr` 없이 완전형 그대로 |
| 38                          | `최적화 실행 {id.slice(0,8)}`                                                                       | `OPTIMIZER_DOMAIN_LABEL.action` 유지(동작 축이라 정합)                                                                                       |
| 82-84 · 88-94               | `획득 함수` `개체군 크기` 등 라벨이 이 파일에만 있음                                                | 라벨 모듈로 이동                                                                                                                             |
| 151 · 211 · 216 · 275 · 280 | `"—"` 리터럴 5곳                                                                                    | `EMPTY_CELL`                                                                                                                                 |

원시 enum 노출이 6종으로 세트에서 가장 많다.

### 5-5. 그 밖의 적용 지점

| 파일                                                                               | 줄            | 현재 상태                                                           | 조치                                           |
| ---------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------- | ---------------------------------------------- |
| `frontend/src/app/(dashboard)/optimizer/_components/optimizer-page-view.tsx`       | 18-22         | `ALGORITHM_LABEL` 이 `그리드 탐색 새 실행` 처럼 라벨+동사를 붙여 둠 | `OPTIMIZATION_KIND_LABEL` + 동사 조합으로 분리 |
| 같은 파일                                                                          | 88-90         | 셀렉트 옵션에 상한이 하드코딩. `베이지안 탐색 (≤ 50회 평가)`        | 상한 숫자는 §6 미해결 참조                     |
| `frontend/src/app/(dashboard)/backtests/_components/status-badge.tsx`              | 9-16          | `queued: 대기 중` · `cancelled: 취소됨`                             | `BACKTEST_STATUS_LABEL` (대기 / 취소)          |
| `frontend/src/app/(dashboard)/backtests/_components/backtest-list.tsx`             | 30-37         | `running: 실행중`(공백 없음) 으로 배지와 불일치                     | `BACKTEST_STATUS_FILTER_LABEL`                 |
| `frontend/src/app/(dashboard)/strategies/new/_components/parse-result-panel.tsx`   | 210-214       | `ok: 변환 완료`                                                     | `PARSE_STATUS_LABEL` (변환 가능)               |
| `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/parse-panel.tsx`    | 220-224       | 같은 Record 복제본. `ok: 변환 가능`                                 | 같은 모듈 참조로 중복 제거                     |
| `frontend/src/app/(dashboard)/backtests/_components/report/trade-ledger-table.tsx` | 328           | `t.direction === "long" ? "롱" : "숏"` 삼항                         | `TRADE_DIRECTION_LABEL`                        |
| 같은 파일                                                                          | 34-35         | 필터 라벨 `롱만` `숏만`                                             | `TRADE_DIRECTION_LABEL` 기반 파생              |
| `frontend/src/app/(dashboard)/backtests/_components/trades/trade-filter-row.tsx`   | 49-50         | 같은 삼항의 세 번째 사본                                            | 같은 모듈 참조                                 |
| `frontend/src/app/(dashboard)/backtests/_components/trades/trade-analysis.tsx`     | 49-50 · 62-67 | `롱` `숏` 리터럴 4곳                                                | `TRADE_DIRECTION_LABEL`                        |

### 5-6. 이식 순서 권고

1. `src/lib/labels.ts` 신설. 다른 모듈이 전부 여기에 의존하므로 먼저 들어가야 한다.
2. `features/trading/labels.ts` + `orders-blotter.tsx` 의 `STATE_META` 이관. 근본 원인 파일이라 여기가 풀리면 `orders-panel.tsx` 는 import 세 줄로 끝난다.
3. `features/optimizer/labels.ts` + 목록·상세 2파일. 원시 enum 노출 9종이 한 번에 닫힌다.
4. `features/backtest/labels.ts` + 배지·필터 값 통일.
5. `features/strategy/labels.ts` + 복제된 `STATUS_LABEL` 2곳 제거.
6. CSS primitive 개명(§3)은 프로토타입 HTML 과 React 스타일 레이어를 함께 건드리므로 별도 슬라이스로 분리한다.

---

## 6. 미해결로 남는 것

프로토타입 화면만으로는 확정할 수 없어 사람 결정이 필요하다.

1. **전략 수명주기 enum 의 존재 여부.** `draft`/`validated`/`deployed` 는 프로토타입 캐논(`_KIT.md:91-95`)에만 있고 `frontend/src/features/strategy/schemas.ts` 에 대응 필드가 0건이다. 백엔드에도 `deployed` 문자열이 없다. 서버 필드를 신설할지, 프로토타입에서 뺄지 결정이 필요하다.
2. **평가 상한 숫자.** 프로토타입은 `베이지안 · 유전 최대 100회`(`screen-09-optimizer-list.html:1162`)이고 실 코드 상수도 `backend/src/optimizer/engine/genetic.py:73` `_MAX_GENETIC_EVALUATIONS: Final[int] = 100` 인데, 프론트 셀렉트는 `≤ 50회 평가`(`frontend/src/app/(dashboard)/optimizer/_components/optimizer-page-view.tsx:89-90`)로 인쇄한다. 같은 파일의 docstring(`genetic.py:19`)도 50 이라고 적어 상수와 어긋난다. 용어가 아니라 숫자 문제이나 화면 카피에 박혀 있어 함께 정해야 한다.
3. **`strategy.backtest_count` 열의 정의.** 화면이 열 이름을 `백테스트` 로만 인쇄해(`screen-06-strategies-list.html:1249`) 완료 기준인지 전체 실행 기준인지 확정할 수 없다. strat_4e18 이 0 인데 원장에는 실행 2건(`run_5b77` 실패 · `run_b0e7d2` 대기)이 있다. 완료 기준이면 정합하고 전체 기준이면 2 여야 한다. 모듈에는 완료 기준으로 가정한 힌트 문구를 넣어 두었다.
4. **OKX 지원 여부.** 프로토타입 캐논은 Bybit 단일(`_KIT.md:89`), 실 코드는 `bybit` + `okx`(`frontend/src/features/trading/schemas.ts:71`)다. **화면 쪽 분기는 2026-07-20 에 닫혔다.** `screen-16-pricing.html:1451` 이 OKX 를 로드맵으로 재분류해 `screen-14`/`screen-17` 과 정렬했고 17벌이 전부 캐논 편이다(§1-C 6행). 남은 질문은 코드 대 캐논이다. "OKX 데모 연결이 실제로 주문까지 오갔는가" 를 실측해야 하며, 오간 적이 없다면 `schemas.ts:71` 의 enum 에서 `okx` 를 빼는 쪽이 화면과 정합한다.
5. **`.chip.warn` 대 `.chip.failed` 개명 범위.** 이 문서는 `warn` 으로 판정했으나(§3-1) 사용 빈도는 `failed` 가 4 대 1 로 우세하다. 개명을 프로토타입 HTML 5파일에도 소급할지, React 쪽만 `warn` 으로 갈지 결정이 필요하다. **2026-07-20 라운드에서도 개명은 하지 않았다.** 화면은 여전히 `chip failed` 4건 · `chip warn` 1건이고, §1-A · §2-2 의 톤 열은 그 실측을 적는다.
6. **`screen-02` 의 `실행 중` 칩 톤 2건.** §1-B B1 이 `chip accent` 로 판정했고 원장 2벌(`screen-03:1374` · `screen-09:1310`)이 그 톤이지만 `screen-02-dashboard.html:1358` `:1374` 는 중립 `chip` 으로 남았다. 이번 라운드에서 배포됨·검증됨 칩은 고쳤는데 실행 중만 빠졌다. 화면 교정으로 닫을 수 있는 유일한 잔여 톤 분기다.
7. **`strat_4e18` 백테스트 건수.** §6-3 과 같은 뿌리다. `screen-06-strategies-list.html:1669-1672` 이 자기 감사 주석에 "이 화면은 0건인데 실행 원장에는 완료 실행 2건(`run_c3e77a` · `run_6e0b82`)이 있다" 를 미해소로 적어 두었다. 다만 `screen-03:1706` 은 `run_c3e77a` 를 `strat_7a31`(MA Crossover) 소속으로 판정한다. **두 화면의 귀속 주장이 서로 다르므로 어느 쪽이 원장인지부터 정해야 한다.** 배분을 고치면 nav-count 캐논 48 을 12행에 재배분해야 해서 파급이 크다.
8. **옵티마이저 실행 이력 빈 상태 카피.** `screen-09` 는 보관함 빈 상태와 로드 실패만 그리고 "실행 이력 없음" 카드는 그리지 않는다. 실 코드(`optimizer-run-list.tsx:52·58`)에는 영문 문구가 있으므로 한국어 정본을 새로 정해야 한다. 이전 판본이 `OPTIMIZER_EMPTY_STATE` 에 적어 둔 두 문장은 화면 근거가 0건이라 삭제했다(§4-3).
