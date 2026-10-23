# Gemini 3.8 Flash·3.5 Flash-Lite의 두 EMA 전략·세 언어 비교

**3.8 Flash의 승인된 두 요청을 모두 소비했으며 01은504/timeout, 02는 세 언어 원문을 반환했다.**
실제 확보한 것은 Python·TypeScript·Pine 각1개, 총3원문이며 모두 공개/의미 검증을 통과해
각90/90점이다. 3.8 추가 추론은 종료했다. 3.5 Flash-Lite는 별도 승인·장부로 같은 사례의
언어별 독립6요청에서6원문을 확보했다. Lite는 공개5/6·독립 의미2/5 통과이며1개는 공개 실패로
의미 미실행이다. Lite의 원문으로 3.8의 누락을 채우지 않는다. 두 코호트 모두 추론을 종료했다.

| 모델·조건 | 확보/계획 원문 | 공개 통과/실행 | 의미 통과/실행 | 확보 원문 품질90 |
| --- | --- | --- | --- | --- |
| Sol 6.1 A/direct/rep0 · 과거 단일6요청 읽기 재사용 | 6/6 | 6/6 | 6/6 | 각90 |
| 3.8 Flash · 신규 bundle2요청 | 3/6 | 3/3 | 3/3 | 각90(02만 확보) |
| 3.5 Flash-Lite · 신규 단일6요청 | 6/6 | 5/6 | 2/5 | 평균62.0915(공개 실패0 포함) |

3.8의 미확보3개는 아래 생성 실패 정책0과 구분해 표시한다. 이 표의 확보 원문 평균에
존재하지 않는 원문을 섞지 않는다. 모델만 통제한 순위나 일반적 우열을 의미하지 않는다.

## 대상과 비교 조건

기존 Sol `full-v2/manifest.json`의 첫 두 사례를 순서로 고정했다. `01`은 EMA20/50 교차,
`02`는 EMA 추세 눌림 복귀다. DEV D01~D06이나 성과로 고른 사례가 아니다. 공개 계약과
언어별 계약·사례 prompt를 원문 그대로 사용했다. Sol 원문·숨은 정답·검증 결과를 생성
프롬프트나 수리 피드백에 전달하지 않았다.

Gemini 3.8 Flash는 사례마다 Python·TypeScript·Pine을 함께 반환하는 bundle JSON을
요청했다. **API 요청2개에서 원문6개를 계획**했으며, 각 요청은 `case_id`와 세 언어의
`language`·`source_code`·`assumptions`를 엄격히 검사한다. 중복·누락·추가 필드와 잘못된
사례 ID를 허용하지 않고 생성 원문을 수리하지 않는다.

비교 대상은 Sol 6.1의 **A/direct/rep0**에 정확히 대응하는6개다. 과거 manifest의 effort는
`high`이며 현재 구현 세션의 reasoning 설정과 다르다. 기존 Sol은 언어별 개별 요청이었다.
과거 요청 모델은 `gpt-6.1-sol`이지만 응답의 실제 모델 attestation은 보존되지 않아 `UNKNOWN`이다.
과거 Sol CLI에는 도구·검색·셸·파일·생성 코드 실행을 금지하는 별도 접두문도 있었다.
Gemini는 세 언어가 요청 하나의 출력 상한16,384토큰을 공유한다. **모델만 통제한 우열 평가가
아니다.** 추가 sampling·thinking override 없이 기존 Gemini Developer API adapter를 사용한다.
Sol의 `high`와 Gemini의 기본 thinking을 같은 추론 예산으로 간주하지 않는다.

Sol의 source·trial·semantic18파일을 봉인 archive와 대조해 모든 hash의 일치를 확인했다.
기존 공개/의미 통과와 품질90=90을 읽기만 했으며 새 Sol 생성·기존1,350건 재평가는 하지 않았다.
기존80회 Gemini Python cohort와 PR #926도 변경하지 않았다.

## 3.8 Flash: 예산과 실제 관측

부모가 동일 무료 프로젝트를 새로고침한 관측시각은 2026-10-23 05:26:38 UTC다.
3.8 Flash 표시값은2/5 RPM·2.48K/250K TPM·12/20 RPD였다. 기존 보수 예약 장부는
초기400을 포함해13회이며 `20 − max(UI12, 장부13) − 예비5 = 추가2`로 제한한다.
화면은 최근1일 최대 사용량과 최대15분 지연을 알린다. 외부 동시 사용도 관측하지 못했으므로
**현재 실시간5회가 남는다는 보장은 아니다.** 정확한 당일 누적·보장 잔여는 `UNKNOWN`이다.

각 호출 전에 예약을 fsync하며 실패·중단 예약도 소비로 남긴다. 추가 probe·SDK retry·
continuation·repair·다른 모델/provider fallback은0이다. 모델별 동시1·최대4 RPM을 지키고,
2026-10-23 07:00 UTC 이후에는 `NOT_RUN`으로 남기며 다음날 자동 실행하지 않는다.
실제 청구액은 확인하지 않았으므로 `UNKNOWN`이다.

두 예약은 각각05:36:44·05:39:44 UTC에 네트워크 호출 전에 기록됐다.05:42:05 UTC에
두 번째 요청이 끝났으며 이후3.8 추론은0회다. 기존13+신규2=보수 장부15회, 예비5회다.

| 사례 | 요청 provider/model | 실제 응답 model | 결과·finish reason | 지연 | 보고된 토큰 입력/출력/thinking/합계 |
| --- | --- | --- | --- | --- | --- |
| 01 EMA20/50 교차 | gemini / gemini-3.8-flash | UNKNOWN | 504·timeout / UNKNOWN | 180.704초 | UNKNOWN |
| 02 EMA 추세 눌림 복귀 | gemini / gemini-3.8-flash | gemini-3.8-flash | 완료 / STOP | 140.679초 | 1,707 / 2,696 / 2,093 / 6,496 |

01은 원문·usage·finish reason·실제 model 응답이 없다. SDK가 보고한504를 보존했으며
누락을0토큰으로 바꾸지 않는다. 02 토큰은 세 언어 bundle 전체의 값이며 언어별로 배분하지 않는다.
파싱된 JSON과 provider가 보고한 metadata를 보존했지만 원시 HTTP 응답은 수집하지 않았다.
요청 성공은1/2, 계획한 원문 확보는3/6이다. 하나의 bundle 실패를 독립적인 언어별 실패3건으로
해석하지 않는다. 지연에는 실패 요청의 timeout이 포함되며 생성·실행 속도 우월성을 뜻하지 않는다.

## 3.8 Flash: 원문별 결과

| 사례 | 언어 | 기존 Sol 공개/의미·품질90 | Gemini 원문 | Gemini 공개360봉 | Gemini 독립 의미1,200봉 | Gemini 품질90 |
| --- | --- | --- | --- | --- | --- | --- |
| 01 | Python | 통과/통과·90 | 없음 | NOT_RUN | NOT_RUN | 생성 실패 정책0 |
| 01 | TypeScript | 통과/통과·90 | 없음 | NOT_RUN | NOT_RUN | 생성 실패 정책0 |
| 01 | Pine | 통과/통과·90 | 없음 | NOT_RUN | NOT_RUN | 생성 실패 정책0 |
| 02 | Python | 통과/통과·90 | 확보 | 통과 | 통과 | 90 |
| 02 | TypeScript | 통과/통과·90 | 확보 | 통과 | 통과 | 90 |
| 02 | Pine | 통과/통과·90 | 확보 | 통과 | 통과 | 90 |

01의0은 생성부터 포함한 기존 평가 정책의 점수다. 존재하지 않는 원문의 실행·의미 품질은
관측하지 못했다. Sol6개는 봉인 결과를 읽기 재사용했으며 Gemini의 실제 새 평가 수는 확보한
3개로 제한했다. 세 원문 모두 모든 행동·참조 원장 일치, long/short 위험 계약, 재실행 재현성과
prefix 안정성을 통과했다. 현재 확보한 원문을 수정하거나 의미 검증 결과를 모델에게 돌려주지 않았다.

## 3.5 Flash-Lite: 별도 단일 언어 코호트

사용자의 추가 선택 뒤 별도6회 배정을 받았다. 관측시각은2026-10-23 05:55:36 UTC이며
동일 무료 프로젝트에서3.5 Flash-Lite는15 RPM·250K TPM·500 RPD, 표시 사용14 RPD였다.
기존 모델 예약13과 표시값14 중 큰 값14에서 시작해 `14 + 6 = 보수 사용20`, 참고 여유480이다.
최대15분 UI 지연·최근1일 최대값·외부 동시 사용 한계가 있어 보장 잔여로 해석하지 않는다.
실제 invoice는 `UNKNOWN`이다. 3.8은 추가0회로 유지한다.

새 root는 `runs/gemini-language-comparison/lite-single-language-6-v1/`다. 슬롯은
`01/python → 01/typescript → 01/pine → 02/python → 02/typescript → 02/pine`으로 고정했다.
각 요청은 원 Sol의 `PUBLIC_CONTRACT + LANGUAGE_CONTRACT[language] + case.prompt` 조합과
동일한 `CODE_SCHEMA`(`source_code`, `assumptions`, 두 필드 필수·추가 필드 금지)를 사용한다.
각각 독립적인 단일 언어 요청이며 세 언어 bundle과 별도 조건이다.

호출 전 fsync·단일 소유 장부·예약된 슬롯 재호출 금지·오류 포함 최대6회·SDK 추가 retry/
probe/repair/continuation/fallback0을 적용한다. 동시1·최대12 RPM·출력 상한16,384를 쓰며
sampling/thinking override는 없다. 429나 유료 요건 변화에서는 모델을 중단한다.
07:00 UTC 이후의 슬롯은 `NOT_RUN`이며 다음날 자동 실행하지 않는다.

Lite는6/6요청에서6원문을 확보했으며 이후 추가 추론은0회다. 모든 응답의 provider는
`gemini`, 실제 model은 `gemini-3.5-flash-lite`, finish reason은 `STOP`이다.
`thinking_tokens`는 모두 미보고(null)이며0이라고 추정하지 않는다.

| 사례 | 언어 | 생성 지연 | 보고 입력/출력/총토큰 |
| --- | --- | --- | --- |
| 01 | Python | 5.029초 | 1,231 / 1,070 / 2,301 |
| 01 | TypeScript | 2.592초 | 1,241 / 752 / 1,993 |
| 01 | Pine | 3.053초 | 1,313 / 858 / 2,171 |
| 02 | Python | 2.654초 | 1,249 / 716 / 1,965 |
| 02 | TypeScript | 2.621초 | 1,259 / 764 / 2,023 |
| 02 | Pine | 2.438초 | 1,331 / 693 / 2,024 |

전체 입력7,624·출력4,853·보고 총12,477토큰이다. 생성 지연은 n6의 p50=2.637초,
p95=4.535초(선형 보간)다. 원시 HTTP 응답은 수집하지 않았고 파싱된 JSON과 보고된 metadata를
보존했다. 최종 실행·의미·품질 결과는 다음과 같다.

| 사례 | 언어 | 공개360봉 | 독립 의미1,200봉 | 품질90 |
| --- | --- | --- | --- | --- |
| 01 | Python | 통과 | 실패 | 63.9532 |
| 01 | TypeScript | 통과 | 실패 | 63.9532 |
| 01 | Pine | 통과 | 실패 | 64.6429 |
| 02 | Python | 통과 | 통과 | 90 |
| 02 | TypeScript | 통과 | 통과 | 90 |
| 02 | Pine | 실패(`PythonRuntimeError`) | NOT_RUN | 공개 실패 정책0 |

언어별2원문의 평균은 Python·TypeScript 각각76.9766009852, Pine32.3214285714이며
전체6개 평균은62.0915435140이다. 원점수는 불변 평가 JSON에 전체 정밀도로 보존한다.

계획6개 기준 의미 통과는2개다. [확인] 01 Python은 이전 봉 교차에도 epsilon 밖 strict
비교만 적용해 동률에서 벗어나는 교차를 누락한다. TypeScript도 이전 차이를 `< -eps`/`> eps`로
검사해 동률을 제외하고 현재 경계도 계약과 다르다. 두 원문의 실측 macro 행동 정확도는
0.9738300493, 실제 진입18/참조19이며 원장 exact 비교 점수는0이다. **원장0은 손익0이 아니다.**

[확인] 01 Pine은 반대 신호에서 요구된 `short` 대신 `close`가 관측됐고 macro 행동 정확도는
0.9910714286, 진입18/참조19·원장 점수0이었다. 세 의미 실패 원문도 위험 감사·재현·prefix
안정성은 통과했다. 공개 실행과 이 부분 통과를 완전 의미 일치로 취급하지 않는다.

[확인] 02 Pine 원문은 short 포지션에서 long 무효화를, long 포지션에서 short 무효화를
검사해 방향이 뒤바뀌었다. 실제로는 공개 실행에서 `PythonRuntimeError`가 발생해 의미 검증을
하지 않았다. 상세 오류 문자열은 보존하지 않아 공개 실패의 세부 원인은 `UNKNOWN`이다.
정적 무효화 오류를 의미 실패의 실측 원인으로 연결하지 않으며 수리·재생성·추가 실행은 없다.

기존 Sol6개의 과거 보고 입력/출력은147,252/10,389토큰이며 cached 입력130,560과
reasoning 출력6,063은 각각 해당 입력/출력에 포함된 별도 관측이다. 원 `total_tokens` 필드는
미보존(null)이고 입력+출력157,641은 파생 합계다. 과거 생성 지연 n6의 p50/p95는48.918/53.331초다.
Sol CLI wrapper·캐시/추론 토큰 정의·관측시점과 Gemini 조건이 다르므로 이 숫자로 실제 비용이나
모델·코드 실행 속도의 우월성을 결론내리지 않는다.

## 실행과 의미의 경계

새 Gemini 원문만 기존 gVisor의 공개360봉·독립 의미1,200봉으로 평가한다. 원형 Mac
수치 fixture·data hash와 oracle을 사용하며 정규화한 다른 플랫폼 값을 섞지 않는다.
기존 동결 소스63개가 현재 코드와 일치함을 확인했다. 준비봉200·고정 비용·두 완료봉
스윙과 위험 거리10% buffer·1.5R 최초50% 익절·2R 본절/trailing·반전은 기존 공통 원장 계약이다.

품질90은 계약40·원장25·재현15·공개 실행10이다. 공개 실행 통과와 완전 의미 일치를
구분한다. 미실행·미평가는0점으로 채우지 않는다. 생성/공개 실패는 기존 정책에 따라0점이다.
3.8의 실제 생성은 한 전략·언어당1원문뿐이며 Lite는 두 전략·언어당2원문이다. 언어 일반성·수익성·실제 비용·실행 속도 우월성을
결론내리지 않는다. bundle 내 산출물은 독립 API 요청6개가 아니다.

## Antigravity와 Argon

Antigravity는 공식 `antigravity-preview-09-2026` agent를 Interactions API와 remote 환경에서
사용하는 preview이며 Free 프로젝트에도 제공된다. 기본 underlying 모델은3.8 Flash이고
structured output은 지원하지 않는다. 프로젝트 관측 quota는60 RPM·100K TPM·100 RPD,
관측 사용량은0이었다. API가 없거나 무료로 불가능하다는 뜻이 아니다.
[공식 Antigravity 문서](https://ai.google.dev/gemini-api/docs/antigravity-agent)

관리형 agent의 여러 내부 추론·도구 루프가 직접3.8의 quota를 공유하는지, 한 요청이 어떻게
환산되는지는 확인하지 못했다. **예비5 조건의 이번 배정에서는 추가 호출을 보류**하며 실제
agent 추론은0회다. 직접 Gemini의 JSON Schema 요청과 agent 실행을 같은 기능으로 취급하지 않는다.

Argon은 공식 가격표에서 Developer API Free가 제공되지 않으며 이 프로젝트의 RPM·TPM·RPD
관측 한도도 모두0이었다. 이번 배정과 실제 호출 모두0이다.
[공식 가격표](https://ai.google.dev/gemini-api/docs/pricing)

## 3.8 Flash 증거와 재현

비밀 자료와 원문은 gitignore된 `runs/gemini-language-comparison/ema-two-bundles-v1/`에
불변 보존한다. baseline source/trial/semantic18파일과 봉인 선정6행도 복사해 원본을 보존했다.
키는 기존0600 파일에서만 `SecretStr`로 읽으며 원문·로그·보고서·Git에 넣지 않는다.

접착 스크립트와 호출 없는 가짜 응답 검증은 같은 로컬 실험 폴더에만 둔다. 제품/API/FE·
새 공통 하네스·새 런타임은 추가하지 않는다. 접착346줄과 fake 검증193줄을 로컬에 동결했다.
호출 없는 fake9건과 Ruff가 통과했으며 실제 SDK JSON 직렬화·durable 예약·deadline·추가 retry0을
검증했다. 제품 전체 회귀·기존1,350건·경제1,440셀은 재실행하지 않았다.

작업 시작 때 중지돼 있던 전용 `qb-python-research` VM만 원설정으로 기동했다. 평가 종료 후
활성 컨테이너0과 설정 digest·6 CPU·8 GiB 일치를 확인하고 초기 `Stopped` 상태로 복구했다.
소유권·정리 근거는 `vm-ownership.json`·`vm-cleanup.json`에 보존했다. 다른 VM·공유 DB·worker와
호스트 전원 설정은 변경하지 않았다.

주요 파일 SHA-256은 다음과 같다. 아래 경로는 모두 위 실험 폴더 기준이다.

| 파일 | SHA-256 |
| --- | --- |
| `quota-authorization.json` | `9527b4b3c076701171b3d5535a9a414d5dcc92f775fcc71544b60c21868bc695` |
| `sol-manifest.json` | `00722703ed4d92beae9dd51418509e1a3ac1efbbccb46e331c7a214fe47ee177` |
| `prepared-manifest.json` | `954d60e36fab8b51f639fae217f786db9b35fe41dd76dfba240566a571ad14d3` |
| `baseline-audit.json` | `3270601d844826e557c3cf7f37ecc3115e2448f150731b7c555f4fc0f556f0e1` |
| `attempts.jsonl` | `0e366bebc396480187b1b9fa77f48a613cd56453b1b24a04318438b012f4a0a1` |
| `final-summary.json` | `d73b7191e251e511a5426ff4232e35c732279e380cc2c1ca3e0edf31a90eb9eb` |
| `artifact-index.json` | `ed04c34a72edcca856529e3274fcd07b4e4a82244d99a71c7cf1c39c261cf44c` |
| `gemini_language_comparison.py` | `fa99a39830a5770fe90cd2a10a7710f4fd9540ec97aaedd23e6b7260d02e0f0b` |
| `test_language_comparison.py` | `b2a3efe1d8230cc1a6540e8eeda8bfac50ff0cbe0490c3463c8170f9ad257c13` |

사용자 검토용 원문 사본은 추가 개행·수리 없이 bundle의 UTF-8 bytes와 결박했다.

| 원문 사본 | SHA-256 |
| --- | --- |
| `sources/02/strategy.py` | `33cdc212174392cb5fa43247b08b2312e076b491b9f93f08e89ccf8619e432a0` |
| `sources/02/strategy.ts` | `0fe5bd8c42f6ab3b5ee4057b5bf31549e721dd6f09a248288b130a2fa9fd1cf3` |
| `sources/02/strategy.pine` | `3f500e90cbf114613e1fded21e2353ddc6ee4d3590a1e60769f7c5c7663f93ec` |

Mac의 원형 수치 fixture는 공개360봉 digest
`e157a043d0976ad37e76a22222728118ac2c07d12f12eea739357ce4846d35f4`,
의미1,200봉 digest `e8e66bbd5153d51b010bc789b0af9ad58a78614cb0a2f3be156cf9c45805684e`다.
의미 평가의 실제 data hash는 compact JSON 직렬화의
`47d821d7ec8bc08bb6c77edcaa068ed62053e4c1637fda9eb640a54791ca8d0e`이며 같은 봉 값이다.

외부 HTTP 없는 fake 검증 명령:

```bash
apps/api/.venv/bin/python -m unittest discover \
  -s runs/gemini-language-comparison/ema-two-bundles-v1 \
  -p test_language_comparison.py -v
```

기존 gVisor 평가 재현 명령은 다음과 같다. 소유권·원설정·이미지 hash를 확인한 연구 VM이
실행 중이어야 하며, 저장된 평가가 같은 manifest/source hash이면 재사용한다. 호스트 비격리
실행으로 대체하지 않는다. 이 명령은 API 추론을 하지 않는다.

```bash
set -a; . apps/api/.env.local; set +a
DOCKER_HOST=unix:///Users/woosung/.lima/qb-python-research/sock/docker.sock \
  apps/api/.venv/bin/python \
  runs/gemini-language-comparison/ema-two-bundles-v1/gemini_language_comparison.py \
  evaluate --run-dir runs/gemini-language-comparison/ema-two-bundles-v1
```

문서 전용 후속 PR은 `feat/gemini-python-generation`을 base로 한다. 현재 CI의 PR base 필터는
`main`·`stage/**`이므로 이 base에서는 workflow가 발화하지 않는다(`NOT_TRIGGERED`).
제품 회귀를 실행 성공이나 job `SKIPPED`로 세지 않으며 전체 회귀를 수동 dispatch하지 않는다.
실제 검사 대상 head·workflow 존재 여부는 후속 PR Checks와 본문의 검증 기록으로 확인한다.

## 3.5 Flash-Lite 증거와 재현

Lite의 입력·승인·예약·파싱 응답·평가·원문 사본은 별도 root에0600·불변 파일로 보존했다.
생성 동결본의 호출 없는 fake7건은 상한·실패 소비·중복 예약·429/deadline·SDK6요청 직렬화를
통과했다. 실제 생성은6회 뒤 종료했으며 이후 guard 추가는 평가 경로만 변경했다.
생성 스크립트 bytes를 `generation-glue.py`로 보존했고 기존 승인 binding과 생성 ledger를
덮어쓰지 않았다. 평가 직전 기존 `previous.verify_runtime`으로 현재 snapshot을 대조해
소스63개·이미지·endpoint·원 Mac 데이터를 확인했다. 원 Sol/3.8의 평가를 다시 실행하지 않았다.
Lite 작업 소유 VM도 종료 후 활성 컨테이너0·원설정 일치를 확인하고 `Stopped`로 복구했으며
`vm-cleanup.json`에 보존했다. 후속 재평가·VM 재기동·추가 추론은 없다.

다음 경로는 `runs/gemini-language-comparison/lite-single-language-6-v1/` 기준이다.

| 파일 | SHA-256 |
| --- | --- |
| `input-manifest.json` | `826ee89ce7c70780002bf19b09a9f0a72616c8ad3b87c71c604d26af4a61472e` |
| `quota-authorization.json` | `f88930d6e88232641ad92606e68fc744a62a1ed9aad79294f6d168309534f759` |
| `prepared-inputs.json` | `0c58f3f15e996a8fe7a059c384bdf665a77ee391660c07ed44295558bb7f4db4` |
| `authorization-binding.json` | `a26418de88487454c891204ffa15758e859777cdfa13ab6b2a4f15433e0d1f9f` |
| `attempts.jsonl` | `a4aa27810df4feb192e6767bc306f8c051df988f583cd85a7653badb33ad4109` |
| `final-summary.json` | `badae952ad0f3109d031cf26fced4b88e2e9d8f31daf9397b7671edb7050b178` |
| `artifact-index.json` | `ac0c09b40bef7bc652e693a9e53fb77de72440d8e769a574c9876006bc2b32f1` |
| `generation-glue.py` | `dbf2bf725b22ea3ff232f666f248854f3aa719ac08c2d48287357f5236b21711` |
| `lite_single_language.py`(평가 guard 포함) | `9c2af6396f65c3fc041ab587547a087f033d9a27feabd8759ee3d816b6a9da97` |
| `evaluation-runtime-guard.json` | `e56778c10d432d5f1c907fde52cd63ba9fa336b626e19217eafba59175c90f3b` |
| `historical-sol-generation-metadata.json` | `08559b063e9e0c873b59ce442f844056afc72b1c7aef5609db25dbd95f1274d5` |
| `lite-original-sources.zip` | `6e9027ceb5e0290aad3b8d0bbde18da8f96879ba80d5aadf9028bf4163dabe35` |

확장자별 검토 사본은 원문 bytes 그대로이며 `source-copies.json`과 결박했다.

| 사본 | SHA-256 |
| --- | --- |
| `sources/01/python.py` | `8120ca9152d1fea7558d048607bf8f020c337503b3014563cf48e183a56ab48c` |
| `sources/01/typescript.ts` | `ce5e95c9ad6e99ba9d639104f2a5bc575464fa31f2701ec115abb482c86fcd28` |
| `sources/01/pine.pine` | `d68b61997923cbe7f5af92d2f2dc123317daa9d95455a81b7d24500327f5d7e7` |
| `sources/02/python.py` | `57ff8234735b6321ffc2a2b8b9ac5747c1554b80253c090f36c1e797cfa39514` |
| `sources/02/typescript.ts` | `6d8b533c5e65a5134b48e1849011b85d9064ff9f29638ac187c8dec6ef2ce852` |
| `sources/02/pine.pine` | `7a52282c81bae3f97864468a78b5a4e3076a3aa38d8439ecb541d632edfc216a` |

호출 없는 fake 재현 명령:

```bash
apps/api/.venv/bin/python -m unittest discover \
  -s runs/gemini-language-comparison/lite-single-language-6-v1 \
  -p test_lite_single_language.py -q
```

소유권을 확인한 원설정 연구 VM에서 새 Lite 평가만 재현하는 명령이다. 입력·원문이 같은
평가 캐시를 재사용하며 API를 호출하지 않는다. 환경 guard가 실패하면 실행을 중단한다.

```bash
set -a; . apps/api/.env.local; set +a
DOCKER_HOST=unix:///Users/woosung/.lima/qb-python-research/sock/docker.sock \
  apps/api/.venv/bin/python \
  runs/gemini-language-comparison/lite-single-language-6-v1/lite_single_language.py \
  evaluate --run-dir runs/gemini-language-comparison/lite-single-language-6-v1
```
