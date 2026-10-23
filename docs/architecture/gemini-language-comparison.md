# Gemini 3.8의 두 EMA 전략·세 언어 비교

**승인된 두 요청을 모두 소비했으며 01은504/timeout, 02는 세 언어 원문을 반환했다.**
실제 확보한 것은 Python·TypeScript·Pine 각1개, 총3원문이며 모두 공개/의미 검증을 통과해
각90/90점이다. 3.8 추가 추론은 종료했고 다른 모델의 추가 추론도0회다.

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
Gemini는 세 언어가 요청 하나의 출력 상한16,384토큰을 공유한다. **모델만 통제한 우열 평가가
아니다.** 추가 sampling·thinking override 없이 기존 Gemini Developer API adapter를 사용한다.

Sol의 source·trial·semantic18파일을 봉인 archive와 대조해 모든 hash의 일치를 확인했다.
기존 공개/의미 통과와 품질90=90을 읽기만 했으며 새 Sol 생성·기존1,350건 재평가는 하지 않았다.
기존80회 Gemini Python cohort와 PR #926도 변경하지 않았다.

## 예산과 실제 관측

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
두 번째 요청이 끝났으며 이후 추론은0회다. 기존13+신규2=보수 장부15회, 예비5회다.

| 사례 | 요청 provider/model | 실제 응답 model | 결과·finish reason | 지연 | 보고된 토큰 입력/출력/thinking/합계 |
| --- | --- | --- | --- | --- | --- |
| 01 EMA20/50 교차 | gemini / gemini-3.8-flash | UNKNOWN | 504·timeout / UNKNOWN | 180.704초 | UNKNOWN |
| 02 EMA 추세 눌림 복귀 | gemini / gemini-3.8-flash | gemini-3.8-flash | 완료 / STOP | 140.679초 | 1,707 / 2,696 / 2,093 / 6,496 |

01은 원문·usage·finish reason·실제 model 응답이 없다. SDK가 보고한504를 보존했으며
누락을0토큰으로 바꾸지 않는다. 02 토큰은 세 언어 bundle 전체의 값이며 언어별로 배분하지 않는다.
파싱된 JSON과 provider가 보고한 metadata를 보존했지만 원시 HTTP 응답은 수집하지 않았다.
요청 성공은1/2, 계획한 원문 확보는3/6이다. 하나의 bundle 실패를 독립적인 언어별 실패3건으로
해석하지 않는다. 지연에는 실패 요청의 timeout이 포함되며 생성·실행 속도 우월성을 뜻하지 않는다.

## 원문별 결과

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

## 실행과 의미의 경계

새 Gemini 원문만 기존 gVisor의 공개360봉·독립 의미1,200봉으로 평가한다. 원형 Mac
수치 fixture·data hash와 oracle을 사용하며 정규화한 다른 플랫폼 값을 섞지 않는다.
기존 동결 소스63개가 현재 코드와 일치함을 확인했다. 준비봉200·고정 비용·두 완료봉
스윙과 위험 거리10% buffer·1.5R 최초50% 익절·2R 본절/trailing·반전은 기존 공통 원장 계약이다.

품질90은 계약40·원장25·재현15·공개 실행10이다. 공개 실행 통과와 완전 의미 일치를
구분한다. 미실행·미평가는0점으로 채우지 않는다. 생성/공개 실패는 기존 정책에 따라0점이다.
계획은 두 EMA 전략이었지만 실제 생성은 한 전략·언어당1원문뿐이다. 언어 일반성·수익성·실제 비용·실행 속도 우월성을
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

## 증거와 재현

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
