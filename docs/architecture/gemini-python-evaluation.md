# Gemini 무료 API의 실행 Python 생성 비교

## 측정 경계

사용자가 승인한 동일 프로젝트·임시 키의 AI Studio Free 상태와 모델별 nonzero 한도를
확인했다. `models.list`는 지정한7종을 모두 반환했다. 목록 등재·무료 등급·실제 접근 성공은
별개다. 정확한 당일 누적 사용량과 보장 잔여는 미관측이며, 화면은 지난1일 peak와 최대15분
지연을 알렸다. 관측시각은 2026-10-23 03:28:17 UTC, quota 일자는 Pacific 2026-10-22다.
청구 내역을 조회하지 않았으므로 실제 청구액은 `UNKNOWN`이다.

추론 상한91회는 availability·품질 생성·모든 재시도·제품 확인을 합친다. SDK 전체 시도1회,
추가 재시도0회이며 전역 병렬2·모델별1이다. 모델별 RPM의80% 이하로 예약하고 429면 그
모델을 중단한다. 한도0 Pro2종·Argon과 이미지·음성·embedding은 호출하지 않는다.
관측 headroom을 보장 잔여로 바꾸거나 TPD 미표시를0으로 채우지 않았다.

catalog 표시이름은 설명용이며 요청은 아래 API ID로 고정했다. TPM 관측 한도는7종 모두
250,000이다. RPM/RPD는 이번 프로젝트 화면의 관측치이며 전역 무료 보장값이 아니다.

| catalog 표시이름 | 요청 API ID | 관측 RPM/RPD | 관측 peak RPD / 참고 headroom |
| --- | --- | --- | --- |
| Gemini 3.8 Flash | `gemini-3.8-flash` | 5 / 20 | 0 / 20 |
| Gemini 3.6 Flash | `gemini-3.6-flash` | 5 / 20 | 0 / 20 |
| Gemini 3.5 Flash Lite | `gemini-3.5-flash-lite` | 15 / 500 | 2 / 498 |
| Gemini 3.1 Flash Lite | `gemini-3.1-flash-lite` | 15 / 500 | 0 / 500 |
| Gemini 3 Flash Preview | `gemini-3-flash-preview` | 5 / 20 | 0 / 20 |
| Gemini 2.5 Flash | `gemini-2.5-flash` | 5 / 20 | 0 / 20 |
| Gemini 2.5 Flash-Lite | `gemini-2.5-flash-lite` | 10 / 20 | 0 / 20 |

3.5 Lite의 관측 peak는5 RPM·24.72K TPM·2 RPD이며 나머지는0이었다. 이 peak를 당일
정확한 누적이라고 부르지 않는다. `rpd_used_today_exact`·`rpd_remaining_guaranteed`는
모두 `null`로 보존했다. 2.5 두 모델은 이 키에서 실제 생성에 성공했지만 다른 신규 프로젝트의
기존 사용자 접근 제한까지 해소됐다는 주장은 하지 않는다.

초기7개 probe는 모두 HTTP400이었다. 원본 장부·요청·실패·manifest는 보존했다.
SDK의 OpenAPI `response_schema` 대신 JSON Schema를 원형대로 전달하는
`response_json_schema`로 공통 전송을 수리하고 실제 SDK 직렬화 회귀를 추가했다.
후속 epoch는 원7회를 소비 예산에 결박하며 추가 hold probe 없이 첫 D01 생성으로 접근을
확인한다. 후속 품질 생성 상한84와 합쳐 전체91을 유지한다. 초기400은 모델의 의미 오류나
영구 접근 불가를 증명하지 않는다. 원 실패를 지우거나 성공으로 재분류하지 않는다.

품질 입력은 기존 공개 D01~D06(SMA·Donchian·RSI/EMA·MACD·UTC VWAP·수동 HA)×2회다.
동일한 제품 prompt·JSON Schema·준비봉200·params와 출력 상한16,384토큰을 사용했다.
sampling과 thinking override는 생략했다. 모델별 기본 사고량은 같다는 뜻이 아니다.
SDK I/O timeout은180초이며 호스트 전체 wall time의 정확한180초 상한으로 해석하지 않는다.
공식 변경사항에 따라3.6/3.5 Lite 이후의 `temperature`·`top_p`·`top_k`와 model prefill을
보내지 않았다. 3.8이 지원하지 않는 thinking `minimal`도 보내지 않았다. 같은 공통 설정을
사용했지만 모델별 기본 thinking이 달라 계산량까지 통제한 실험은 아니다.
숨은 기준·오류를 생성 모델에 되먹이거나 생성 원문을 수리하지 않는다. 이전 Sol1,350건과
경제1,440셀은 재실행하거나 Gemini 점수로 복사하지 않는다.

## 결과와 점수

실제 생성·격리 실행·의미 검증의 종결 결과를 별도로 집계한다. `quality90`은 계약40·공통
원장25·재현15·공개 실행10의 기존 정의다. 공개 실행10점은 UI·SQL·실거래소 검증 점수가
아니다. 생성/공개 실패는 원 정책대로0점이며 미실행·미평가는 `UNKNOWN`으로 유지한다.
반복2개를 먼저 전략별 평균하고 고정6전략을 같은 비중으로 합친다. 의미 이진 통과율과
부분 품질 점수를 구분하며, 수익률·경제 평가·실주문 승인을 점수에 섞지 않는다.

총80/91회를 사용했다. 원probe7회와 후속 품질73회이며 미완 예약은0이다. 3.6은 첫 품질
요청에서503을 받아 나머지11개를 `NOT_RUN`으로 남겼다. 나머지6종은 각12회를 완료했다.
잔여11회를 재시도·새 prompt·다음날 호출로 보충하지 않았다. HTTP403/404/429·timeout은
관측0건이며 원probe400은7건이다. 품질 요청73회 중 생성54·실패19회(5037·Python구문9·
`MAX_TOKENS`3)다. 실패 원문을 newline 변환하거나 재생성해 성공으로 바꾸지 않았다.
추론이 아닌 metadata 조회는 `models.list`1회·`models.get`1회로 별도 장부에 남겼다.

생성 원문54개를 기존 연구 전용 VM의 gVisor에서 모두 평가했다. 공개 실행47개 통과·7개
실패, 통과47개 중 완전 의미 일치21개·의미 불일치26개였다. 미평가 생성물은0개다.
생성 실패19개와 공개 실패7개는 품질0점이며3.6의미실행11개는0점으로 채우지 않았다.

표의 생성은 성공/실제 품질 요청, 공개·의미는 성공/고정12개 입력이다. 전체 시도는 초기
400 probe1회를 포함한다. 지연은 후속 요청의 provider 호출 시작부터 payload 검증 종결까지이며
실패도 포함하고 RPM 대기·이전400 probe·gVisor 실행 시간은 제외한다. p95는 표본 선형보간이다.

| 요청 API ID | 전체 시도 | 생성 | 공개 실행 | 의미 일치 | 품질90 | 생성 p50/p95(초) | 품질 요청 실패 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemini-3.8-flash` | 13 | 11/12 | 11/12 | 9/12 | 80.14 | 44.60 / 122.66 | 503×1 |
| `gemini-3.6-flash` | 2 | 0/1 | 미실행 | 미실행 | UNKNOWN | 3.10 / 3.10 (n=1) | 503×1·나머지11 NOT_RUN |
| `gemini-3.5-flash-lite` | 13 | 12/12 | 12/12 | 4/12 | 66.81 | 4.08 / 9.82 | 0 |
| `gemini-3.1-flash-lite` | 13 | 7/12 | 7/12 | 1/12 | 37.77 | 2.70 / 3.41 | Python 구문×5 |
| `gemini-3-flash-preview` | 13 | 5/12 | 5/12 | 5/12 | 37.50 | 54.04 / 74.89 | 503×4·MAX_TOKENS×3 |
| `gemini-2.5-flash` | 13 | 8/12 | 8/12 | 2/12 | 46.12 | 45.51 / 55.46 | 503×1·Python 구문×3 |
| `gemini-2.5-flash-lite` | 13 | 11/12 | 4/12 | 0/12 | 14.93 | 4.98 / 8.48 | Python 구문×1 |

품질90의 관측 순서는3.8 Flash→3.5 Lite→2.5 Flash→3.1 Lite→3 Flash Preview→2.5 Lite다.
3.6은 순위에서 제외한다. 후속73회 지연은 p50 8.50초·p95 93.69초이며 초기 요청 형식 오류까지
포함한 실제80회 중 실패는26회(32.5%), 후속73회 중 생성 실패는19회(26.0%)다. 이 작은
동일6전략의 반복은 독립 전략12개 표본이 아니므로 근소한 점수 차이를 모집단 차이로 해석하지
않는다. 3.1 Lite의 한 원문은 매 봉 전체 날짜·지표를 재계산해 격리 평가가 길었으며, 생성
지연이 실행 효율을 대표하지 않는다는 한계도 확인됐다.

공개 실행은 응답 계약·실행 가능성을 검사하므로 거래0건도 통과할 수 있다. 독립 의미 검증은
외부 long/short 포지션과 반전·청산 기회를 추가한다. 실제 실패에는 반대 진입보다 무효화
청산을 먼저 반환하거나 청산 의도 하나를 누락한 원문이 있었다. 공통 원장의 위험 관리와
재현성 통과만으로 생성된 신호의 완전 일치를 주장하지 않는다.
2.5 Lite의 공개 실행 실패7건은 `PythonRuntimeError`로 기록됐다. 원문 정적 검토에서는
2건이 비어 있는 `params`의 `warmup_bars`를 필수 조회했고,5건은 문자열 OHLCV를 숫자로
변환하지 않고 산술·평균·실수 비교에 사용했다. 원 하위 예외 본문은 보존하지 않았으므로
이를 실제 `KeyError`·`TypeError`를 재현한 결과라고 바꾸어 적지 않는다.

provider는80회 모두 Gemini로 고정됐다. 아래는 실제 보고된 토큰의 합이며 실패 응답에서
관측된 usage도 포함한다. 괄호는 보고된 요청 수/실제 요청 수다. 빈 관측을0으로 합산하지
않았다. `total`은 provider 보고값이며 임의로 입력·출력·thinking을 다시 합친 값이 아니다.

| API ID | 입력 | 출력 | thinking | total |
| --- | --- | --- | --- | --- |
| `gemini-3.8-flash` | 14,651 (11/13) | 13,429 (11/13) | 15,669 (11/13) | 43,749 (11/13) |
| `gemini-3.6-flash` | UNKNOWN (0/2) | UNKNOWN (0/2) | UNKNOWN (0/2) | UNKNOWN (0/2) |
| `gemini-3.5-flash-lite` | 16,016 (12/13) | 12,378 (12/13) | UNKNOWN (0/13) | 28,394 (12/13) |
| `gemini-3.1-flash-lite` | 16,016 (12/13) | 8,798 (12/13) | UNKNOWN (0/13) | 24,814 (12/13) |
| `gemini-3-flash-preview` | 10,680 (8/13) | 6,460 (8/13) | 87,318 (8/13) | 104,458 (8/13) |
| `gemini-2.5-flash` | 14,651 (11/13) | 28,680 (11/13) | 85,099 (11/13) | 128,430 (11/13) |
| `gemini-2.5-flash-lite` | 16,016 (12/13) | 17,840 (12/13) | UNKNOWN (0/13) | 33,856 (12/13) |

전체 관측 합은 입력88,030·출력87,585·thinking188,086·total363,701이다. 입력/출력/total은
각66회 보고·14회 미보고, thinking은30회 보고·50회 미보고다. 별도 thinking을 보고하지 않은
Lite 응답을 thinking0이라고 부르지 않는다. 응답 모델은3.6의2회와 나머지 HTTP오류12회를
제외한66회에서 해당 요청 API ID와 같았다. catalog의 `version`은 실제 응답 모델 ID를
대신하지 않는다. 완료 이유는 `STOP`63·`MAX_TOKENS`3·미보고14회다.

## 제품 적용과 해석

[Python preview 계약](../development/gemini-python-generation.md)은 사람이 검토하고
적용·저장한 뒤 기존 백테스트를 별도로 누르는 흐름이다. 모델은 `GEMINI_MODEL` 설정을 따르며
관측 순위로 자동 교체하지 않는다. 기존 Pine 정본·읽기 전용 Python 생성 DTO는 유지한다.

목적별 검토 후보는 다음과 같다. 통과한 원문만 골라 재생성하거나 숨은 정답에 맞춰 모델·
prompt를 최적화하지 않았다. 아래 해석은 고정 소규모 cohort의 운영상 비교이며 기본값
변경 또는 모델의 일반적인 우월성 판정이 아니다.

1. 의미 충실도를 우선 검토할 때는3.8 Flash가 관측 후보다. 완전 의미 일치9/12와 높은 부분
   품질을 보였지만 생성 지연 p95 약123초·관측20 RPD라 빠른 반복 편집에는 부담이 있다.
2. 빠른 초안과 반복 검토에는3.5 Flash-Lite가 관측 후보다. 생성12/12·p50 약4초·관측500 RPD를
   보였지만 완전 의미 일치는4/12이므로 사람이 신호·반전·청산을 검토해야 한다.
3. 3.1 Lite의 낮은 생성 지연만으로 실행 효율을 추정하지 않는다. 구문 실패5건과 전체 이력의
   날짜·지표 재계산 원문이 있었다. 2.5 Lite도 생성11/12와 달리 공개 실행은4/12였다.
4. 3 Flash Preview의 성공 원문5개는 의미 검증을 통과했지만5034건·출력 한도3건이 있었다.
   통과 원문만 고르면 실제 실패율을 숨긴다. 3.6은5031회뿐이라 추천·배제 판단을 보류한다.

검토 후 명시적으로 선택할 때의 설정 예시다. 기존 기본 모델은 이7종 실험의 대상이 아니며
가용성을 새로 증명하지 않았다. 키는 승인된 비밀 설정으로 별도 주입하며 예시에 적지 않는다.

```dotenv
LLM_PROVIDER_ORDER=gemini
GEMINI_MODEL=gemini-3.8-flash
```

빠른 초안을 검토하는 선택은 위 `GEMINI_MODEL`만 `gemini-3.5-flash-lite`로 명시한다.
출력 상한16,384·추가 sampling/thinking override 없음·SDK 전체 시도1이라는 실제 측정
설정을 유지한다. 무료 한도는 프로젝트에서 다시 확인하며 유료 fallback을 두지 않는다.

새 CI Playwright는 실제 인증·전용 DB의 불변 버전 저장을 사용한다. 생성 응답과 백테스트
접수·조회는 대체하므로 실제 Gemini·worker·gVisor 계산 완료의 증거가 아니다. 실제 생성물의
공개 실행과 독립 의미 검증은 별도 연구 gVisor에서 직접 수행한다. 공유 Celery worker를
이 워크트리의 실행 증거로 사용하지 않는다. Demo 활성화·주문·운영 DDL·배포는 하지 않는다.
연구 VM의 원래 CPU·메모리를 유지했고, 검증 완료·컨테이너0개 확인 후 작업 전의 정지
상태로 되돌렸다. 다른 세션의 DB·worker·VM은 재기동하지 않았다.

## 증거와 재현

원본은 gitignore된 `runs/gemini-python-eval/`, 후속 생성·평가는 `cohort-v2/`에 둔다.
Free·quota·키 연결의 비밀 자료와 실제 생성 원문은 Git에 올리지 않는다. manifest는 공개
계약·프롬프트·스키마·소스·입력 데이터·Docker 이미지·endpoint와 원probe 장부를 결박한다.
동일 원문·동일 입력·미래 prefix·외부 long/short 포지션 probe·공통 원장을 독립 검사한다.
다른 모델·새 원문·다른 실행 환경으로 실패 결과를 덮어쓰지 않는다.

최종 로컬 증거의 SHA-256은 다음과 같다. 키·프로젝트 식별자는 공개하지 않으며 해시는
비밀 파일을 공개하는 대신 이 측정의 실제 산출물 원본을 식별한다.

| `cohort-v2/` 파일 | SHA-256 |
| --- | --- |
| `manifest.json` | `91a76339b8a6b5ebb61b47c4666f458d87f13f2f29d0b5e251cb00574d55dec1` |
| `attempts.jsonl` | `b5be44c7e776d096d3d658f849e394e9008f7422fb3006cca6f9b939dc2516c3` |
| `report.json` | `6691141d751fdb7f438c6bbfc39c881804028bb2dd40ac22a4f28d22d1612730` |
| `generation-audit.json` | `9ba1e64cf95d8b2e38ef0439ece1a796b259fd51076a6fd040d6e8584ef2f250` |

제품과 검증의 최종 head·실제 CI 상태는 [PR #926](https://github.com/woosung-dev/quantbridge/pull/926)의
본문과 Checks가 갖는다. 생성 자체가 중단돼도 원 예약은 소비로 남으며 재호출하지 않는다.
소규모 고정6전략·각2회의 순위와 표본 p95는 시장 전반의 정확성·모집단 우월성·미래 SLA를
보증하지 않는다. 검증 통과가 수익성 또는 Demo 운영 적합성을 뜻하지 않는다.

공식 근거: [모델 목록](https://ai.google.dev/api/models),
[JSON Schema 출력](https://ai.google.dev/gemini-api/docs/generate-content/structured-output),
[3.6/3.5 Lite 파라미터 변경](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6),
[3.8 thinking](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[프로젝트 단위 quota](https://ai.google.dev/gemini-api/docs/rate-limits).
