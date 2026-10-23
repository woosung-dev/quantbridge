# Gemini 3.8 Flash의 Sol 약점 기반 hard9 비교

**9회 예약·완료로 신규 추론을 종료했고 실제 확보한7원문만 평가했다. 공개4/7·완전 의미2/4 통과다.**
Python29는503, TypeScript09는429로 원문이 없으며 두 코드의 실제 품질은 `UNKNOWN`이다.
기존11+신규9=자체 장부20회다. 429가 RPM/RPD 중 어느 한도인지는 확인하지 못했다.
기존 Sol 결과에서 언어별 세 항목을 고정해 Gemini 3.8 Flash의 새 단일 요청9회를
관측했다. 이 문서는 두 EMA 사례의 [기존 비교](./gemini-language-comparison.md)와 별도다.

## 질문과 선정 경계

기존 Sol `A/direct`450건에서 언어마다 과거 취약 표본 두 항목과 구조상 중상 이상으로 보는
한 항목을 선정했다. Python·TypeScript·Pine 각3개, 전체9개다. 기존 원문·trial·의미
평가262개 파일의 봉인 대조를 완료했고 **새 Gemini 결과를 보기 전에** 선정 파일을 동결했다.
이 문서에는 `parent-selection.json`의 선정9행만 반영했으며 기존450건을 재검사하지 않았다.

| 언어·사례 | 동결 제목 | 선정 구분 | Sol 기존5회 평균 | Sol 고정rep0 | Gemini 새1회 |
| --- | --- | --- | --- | --- | --- |
| Python29 | Chandelier trend reversal | 과거 취약 | 67.4799 | 61.8499 | 0*(HTTP503; 코드 UNKNOWN) |
| Python30 | closed4h EMA regime | 과거 취약 | 88.9264 | 90 | 90 |
| Python09 | Bollinger squeeze breakout | 중상 이상 가설 | 90 | 90 | 90 |
| TypeScript05 | Supertrend reversal | 과거 취약 | 72 | 0 | 63.8517 |
| TypeScript29 | Chandelier trend reversal | 과거 취약 | 73.1099 | 61.8499 | 0(공개 실패) |
| TypeScript09 | Bollinger squeeze breakout | 중상 이상 가설 | 90 | 90 | 0*(HTTP429; 코드 UNKNOWN) |
| Pine29 | Chandelier trend reversal | 과거 취약 | 0 | 0 | 0(공개 실패) |
| Pine27 | OLS regression channel | 과거 취약 | 54 | 90 | 0(공개 실패) |
| Pine09 | Bollinger squeeze breakout | 중상 이상 가설 | 90 | 90 | 61.0317 |

점수는 품질90이며 표는 소수4자리까지 반올림했다. 기존5회는 rep0..4이고 비교 원문은 rep0로
고정했다. 각 원점수·rep0 source SHA·봉인 baseline 행은 선정 파일에 전체 정밀도로 보존한다.
**Sol5회 평균·고정rep0와 Gemini1회는 반복 수가 다르다.** 한 번의 새 결과를 과거5회의
분포와 동등하게 취급하지 않으며, 시점·CLI/API·추론 설정까지 모델만 통제한 비교도 아니다.

TypeScript11의 평균72는 CLI exit1에 따른 가용성 실패여서 취약 코드 표본에서 제외했다.
선정된 TypeScript05의 compile 실패와 Pine29의 subscript 지원 오류도 수학적 의미 오류로
단정하지 않는다. 공개 실행 실패와 의미 불일치를 구분해 해석한다.

29번의 원 prompt `전봉LL22+3ATR22`는 ATR까지 전봉에 속하는지 수식 범위가 모호하다.
기존 Sol Python·TypeScript 원문은 이전 LL/HH에 현재 `ATR[i]`를 결합했고, 동결 oracle은
이전 LL/HH에 직전 `ATR[i-1]`를 결합한다. 61.849866점·원장 불일치는 **동결 oracle 불일치와
명세 모호성**으로 해석하며 전부 명백한 모델 수학 버그라고 단정하지 않는다. 29번 세 언어
행에 이 주석을 적용한다. 입력·oracle·채점은 봉인 그대로이고 이 해석을 모델에 돌려주지 않았다.

| 기존 baseline | 확인된 실패 유형과 범위 |
| --- | --- |
| TypeScript05 rep0 | `TS7022`의 `nextUpper`/`nextLower` strict 컴파일 실패. wrapper의 `PythonRuntimeError`는 Python 원문 오류를 뜻하지 않음 |
| Pine29 rep0 | `Call[1]` 식 과거 index의 `pine_v2` 지원 오류. 일반 Pine 문법·수학 오류로 확대하지 않음 |
| Pine27 rep2·rep4 | `+=` compound assignment의 `pine_v2` 미지원. 고정 rep0는90점 |

새 TypeScript05는 공개 컴파일을 통과했지만 의미 점수는63.8517이다. 첫 ATR 준비봉의
초기 방향을 `close >= hl2 ? up : down`으로 두는 반면 frozen oracle은 기본 이전 방향을
down으로 두고 상단 돌파 때만 up으로 바꾼다. 첫230봉이 OHLC180·ATR0인 fixture에서
이 초기화 차이는200/201봉의 반대 의도와230봉의 long 누락 관측에 정합한다.
원 prompt는 초기 regime 세부를 명시하지 않으므로 **frozen 기준 초기화 variant 불일치와
명세 모호성**으로 해석한다. 전체 불일치를 이 단일 원인으로 확정하거나 범용 Supertrend
수학 버그라고 부르지 않는다. 기존 Sol05 rep0의 컴파일 실패와 새05의 컴파일 통과 후 의미
불일치는 단계가 다르다. 입력·oracle·채점은 바꾸지 않았고 추가 실행·모델 피드백도 없다.

새 Pine27 원문의 `+=`는 정적으로 `pine_v2` 미지원임을 확인했다. 다만 새 Pine27·29의
실제 공개 결과에는 wrapper `PythonRuntimeError` 외 상세 원인이 보존되지 않았으므로
직접 실패 원인은 `UNKNOWN`이다. 정적 지원 문제를 실측 예외의 확정 원인이나 OLS 계산
오류로 연결하지 않는다.

`hard9`는 **과거 Sol 약점에 기반한 선택 표본**의 이름이며 공식 난도 분류가 아니다.
낮은 Sol 점수가 Gemini에도 어려움을 뜻하는지는 이번 관측의 질문이다. 언어별 취약 항목은
다르며 과거 점수로 고른 데 따른 선택 편향과 평균으로의 회귀 가능성이 있다.
언어별 n=3으로 일반적인 모델·언어 우열이나 모집단 평균을 추정하지 않는다.

과거 Sol 점수와 실행 근거는 동결 자료를 읽기 재사용한다. Sol·Lite 새 생성, 기존450건·
전체1,350건 재평가, 기존80회 Gemini 코호트·경제1,440셀의 재실행은 없다.
선정 근거는 과거 Sol 결과만 사용하며 새 Gemini 결과·숨은 정답으로 사례를 교체하지 않는다.

## 생성 조건과 호출 상한

별도 root는 `runs/gemini-language-comparison/flash-sol-hard9-v1/`다.
각 슬롯은 한 언어의 원문 하나를 요청한다. 세 언어 bundle이나 실패 슬롯의 재요청이 아니다.

| 항목 | 사전 계약 |
| --- | --- |
| 요청 provider / model | `gemini / gemini-3.8-flash` |
| 입력 | 기존 `PUBLIC_CONTRACT + LANGUAGE_CONTRACT[language] + case.prompt` 원문 |
| 응답 | 기존 `CODE_SCHEMA`의 `source_code`·`assumptions` |
| 출력 상한·추론 설정 | `max_output_tokens=16384`, 기본 thinking·sampling 유지 |
| HTTP 대기 | 600초. 각 선정 항목의 원 입력·schema를 유지하며 대기 조건만 완화 |
| SDK 시도 | 요청당1회, 추가 probe·retry·repair·continuation·fallback0 |
| 병렬·속도 | 생성 최대2개, 전역 최대4 RPM, 요청 시작 간격 최소15초 |
| 전체 상한 | 오류·실패·중단을 포함한 예약 최대9회 |

호출 전에 단일 소유 장부에 예약을 기록하고 fsync한다. 예약된 슬롯을 다시 호출하지 않는다.
400·401·402·403·404·429 또는 billing 요건을 관측하면 공유 중단 상태로 신규 호출을 막는다.
중단 전에 이미 시작한 요청도 시도 수에 포함한다. 다른 키·모델·provider로 대체하거나
다음날 자동 재개하지 않는다. 중단으로 남은 슬롯은 미호출로 보존한다.

이번 배정 시작 전 새 키의 로컬 장부는11회이며 상한9회를 더하면 최대20회다. Free 상태는
`USER_CONFIRMED`, 일일 한도20은 `USER_REPORTED` 근거다. 이는 프로젝트 전체의 실시간
잔여를 보증하지 않는다. 외부 사용·project remaining·실제 invoice는 `UNKNOWN`이다.
최종 auth는 동결된 선정9개에 결박됐으며 실행 승인 창은2026-10-23 07:58~10:00 UTC다.
동결된9회만 호출했고 추가 API probe는0회다. 동결 파일의 SHA-256은 다음과 같다.

- `parent-selection.json`: `9426feaf3d66ebef4240f2bea9c28ff7bf7c0f4a195bffe4b5af80794ec37b9b`
- 부모 최종 auth: `9593697023ee570996a6f0f73410c02e3107594529d715ca6aff2a86cb4e0957`

600초 조건은 이전180초 첫 시도·360초 진단과 다르다. 과거 가용성 수치와 합쳐 동일 조건의
성공률·속도 비교로 표시하지 않는다. 이번9개도 완화된 대기 조건의 새 코호트로 보고한다.

## 신호 코드와 공통 위험 원장의 경계

기존30개 case prompt는 공통 위험 계약을 사용하며 별도 risk 전용 전략은 없다.
생성 코드는 완료봉의 진입·청산 의도만 반환하고, 수량·SL·부분 익절·trailing은 공통 broker가
처리한다. 새 코드에 위험 수식을 따로 구현시키거나 이번 연구용 엔진을 만들지 않는다.

두 완료봉은 신호봉과 그 직전 완료봉이다. long은 두 봉의 최저 low, short는 최고 high를
사용한다. 10% buffer는 실제 진입 E와 해당 스윙 사이 거리의10%다. long의 R은
`1.1*(E-L)`, short는 `1.1*(H-E)`이며 R이 양수가 아니면 진입하지 않는다.
공통 broker가 손실 방향1R의 SL, 최초 수량50%의1.5R 익절, 2R 도달 후 본절 보호와
2R 거리 trailing, 반대 신호의 잔량 청산 후 재진입을 처리한다.

`risk_audit` 통과는 **각 생성 전략에서 모든 exit가 실제 발생했다는 증거가 아니다.**
기존 손계산 broker fixture의8개 함수·14개 매개변수 case를 한 번만 실행해14/14 통과했다.
DB·VM·API·생성 코드 실행 없이 기존 trusted broker의 기대값과 실측을 대조한 별도 증거다.

| 손계산 fixture | 기대값·관측값 |
| --- | --- |
| E100·두 완료봉 extreme90/110 | R11, SL 계획89/111, 1.5R 가격116.5/83.5, 2R 활성화122/78·거리22 |
| 최초 수량3의 부분익절 | long/short 수량1.5, 한 번만 체결·다음 봉 중복0 |
| 정확2R 본절과 ratchet | 본절100, 유리한 방향108/92 후 되돌림에도 유지 |
| 실제 trailing·gap SL 체결 | long/short trailing108/92, 불리한 gap SL80/120. 일반 non-gap short SL111 체결을 추가로 관측한 것은 아님 |

불변 `broker-fixture-receipt.json` SHA는
`55e3ded1d9eca7957d280c48a905e43b44e204290dce7a70abe39a02bd495840`이다.
전략별 기존 의미 결과는 `risk_audit.passed`·`entries`만 보고한다. exit별 발생 수는 반환하지
않으므로 새 전략에서 SL·부분익절·trailing이 각각 발생했는지는 `UNKNOWN`으로 표시한다.
별도 fixture 통과로 개별 전략의 exit 발생을 채우거나 전략을 추가 실행하지 않는다.

## 공개 실행·의미 평가와 보존

기존 gVisor 격리 실행기·공개360봉·독립 의미1,200봉 fixture를 사용한다. 평가 병렬은
최대2개이고 Pine을 우선한다. 입력·원문·평가 계약·runtime guard의 hash가 같은 캐시만
재사용하며 기존 원문·점수를 덮어쓰지 않는다.
가능하면 생성과 평가는 별도 lock으로 겹치되 **원문 저장이 끝난 슬롯만** 평가에 넘긴다.
생성 코드에는 키·네트워크·호스트 권한을 전달하지 않는다.

생성 성공, 공개 실행 통과, 완전 의미 일치, 품질90을 구분한다. 완전 의미 통과는
`semantic.status == 'passed'`로 센다. 실제 생성·공개 실행 실패의 정책0과 미호출·미평가의
`UNKNOWN`을 구분하며, 언어별3개 평균과 각 단계의 실행/계획 분모를 함께 공개한다.
수익률을 생성 품질 점수에 섞거나 Gemini 점수에 과거 Sol 점수를 복사하지 않는다.

요청·실제 provider/model, finish reason, 실패 유형, 시도 수, 누락, 원문 SHA와 평가 출처를
남긴다. 보고된 token usage의 부분 합계와 미보고 시도를 구분하고 전체 사용량을 알 수 없으면
`UNKNOWN`으로 표시한다. 실제 비용도 확인 전에는0원이 아니다. 지연은 실패를 포함한
관측 수를 밝히고 p50/p95를 `(n-1)*p` 선형 보간으로 계산한다.
확보 원문은 UTF-8 bytes 그대로 보존하며 계획9개와 실제 확보 개수를 구분한다.

## 새9문항 실측 결과

표의 *는 생성 실패의 전체 파이프라인 정책0이다. 원문 없는 두 슬롯의 코드 수학·실행 품질을
실제로0점으로 측정한 것은 아니다. 공개 실패 원문은 정책0이며 의미 평가는 NOT_RUN이다.

| 슬롯 | 원문 | 공개360봉 | 의미1,200봉 | 품질90 | risk 감사·진입 수 |
| --- | --- | --- | --- | --- | --- |
| 29/python | 없음(HTTP503) | NOT_RUN | NOT_RUN | 0.0000 | UNKNOWN |
| 30/python | 확보 | 통과 | 통과 | 90.0000 | 통과·1 |
| 09/python | 확보 | 통과 | 통과 | 90.0000 | 통과·5 |
| 05/typescript | 확보 | 통과 | 불일치 | 63.8517 | 통과·18 |
| 29/typescript | 확보 | 실패 | NOT_RUN | 0.0000 | UNKNOWN |
| 09/typescript | 없음(HTTP429) | NOT_RUN | NOT_RUN | 0.0000 | UNKNOWN |
| 29/pine | 확보 | 실패 | NOT_RUN | 0.0000 | UNKNOWN |
| 27/pine | 확보 | 실패 | NOT_RUN | 0.0000 | UNKNOWN |
| 09/pine | 확보 | 통과 | 불일치 | 61.0317 | 통과·4 |

실제 공개 실패는 TypeScript29·Pine29·Pine27의3원문이며 wrapper `PythonRuntimeError`만
보존됐다. 하위 직접 원인은 `UNKNOWN`이다. Pine09는 공개 통과 뒤 의미 불일치61.031746점이며
이번 관측만으로 구체 원인을 확정하지 않는다. 원장 불일치 점수0은 손익0이라는 뜻이 아니다.
새 원문 수리·재생성·추가 실행은0이다. risk 감사는 실행된4개 모두 통과했지만 exit별 발생은
별도 입증하지 않았고, 손계산 fixture14/14 통과와 구분한다.

| 언어·계획 각3개 | Sol5회 평균의 평균 | Sol 고정rep0 평균 | Gemini 계획3개 평균 | 원문/계획 | 공개 통과/실행 | 의미 통과/실행 |
| --- | --- | --- | --- | --- | --- | --- |
| Python | 82.1354 | 80.6166 | 60.0000 | 2/3 | 2/2 | 2/2 |
| TypeScript | 78.3700 | 50.6166 | 21.2839 | 2/3 | 1/2 | 0/1 |
| Pine | 48.0000 | 60.0000 | 20.3439 | 3/3 | 1/3 | 0/1 |

전체 계획9개 평균은 Sol5회 평균69.5018·고정rep0 63.7444·Gemini 33.8759다.
Gemini에는 생성 실패2개·공개 실패3개의 정책0이 포함된다. 과거 Sol 약점을 골랐고 반복 수와
실행 환경·추론 설정도 다르므로 이 값으로 일반적인 모델 우열을 결론내리지 않는다.

## 실제 응답·토큰·지연

요청은9회 모두 `gemini / gemini-3.8-flash`다. 원문을 받은7회는 실제 provider/model도
같았고 finish reason은 모두 `STOP`이다. 두 실패는 실제 응답 model·finish·usage가
미보고여서 `UNKNOWN`으로 남긴다. TypeScript29도 보고된 `STOP`·출력20토큰을 그대로
기록하며 MAX_TOKENS나 완료 원인으로 추정해 바꾸지 않는다.

| 슬롯 | 생성 결과 | 지연(초) | 보고 입력/출력/thinking/합계 |
| --- | --- | --- | --- |
| 29/python | HTTP503 | 6.678 | UNKNOWN |
| 30/python | 완료·STOP | 133.371 | 1,313 / 1,514 / 7,347 / 10,174 |
| 09/python | 완료·STOP | 58.046 | 1,360 / 1,602 / 6,445 / 9,407 |
| 05/typescript | 완료·STOP | 32.025 | 1,240 / 1,567 / 2,202 / 5,009 |
| 29/typescript | 완료·STOP | 196.702 | 1,269 / 20 / 15,727 / 17,016 |
| 09/typescript | HTTP429 | 0.382 | UNKNOWN |
| 29/pine | 완료·STOP | 211.801 | 1,341 / 944 / 868 / 3,153 |
| 27/pine | 완료·STOP | 257.569 | 1,342 / 1,438 / 1,438 / 4,218 |
| 09/pine | 완료·STOP | 150.976 | 1,442 / 1,230 / 3,402 / 6,074 |

보고된7회의 부분 합계는 입력9,307·출력8,315·thinking37,429·총55,051토큰이다. 실패2회가
미보고라 전체9회의 사용량은 `UNKNOWN`이며0으로 채우지 않는다. 실패 포함 n9의 생성 지연
p50/p95는133.371/239.262초다. 실제 청구액·프로젝트 식별·실시간 잔여는 `UNKNOWN`이다.

## 완료 근거와 재현

동결 runner의 핵심 fake3건은9회·2동시·15초 간격·실패 소비·공유 중단과 예약 직전 중단
재확인, SDK JSON 본문 동일·600초 timeout·SDK attempt1을 검증했다. 실제 장부는9예약·9완료,
슬롯 중복0·추가 probe/retry/repair/continuation/fallback0이다. 기존11회와 합계20회이고
429 관측 후 신규 예약을 중단한 상태로 모든 추론을 종료했다.

미확보 Python29·TypeScript09는 `resume-candidates.json`에 원입력 hash·실패 metadata만
보존했다. 자동 예약·호출0이며 다음 정상 quota의 **별도 수동 할당이 있어야** 재개할 수 있다.
이번 실험 결과를 덮어쓰거나 새 프로젝트·키 fallback으로 이어가지 않는다.

[검토용7원문 ZIP](../../runs/gemini-language-comparison/flash-sol-hard9-v1/hard9-original-sources.zip)은
로컬 gitignore 실험 폴더에만 보존한다. Python2·TypeScript2·Pine3 원문을 UTF-8 bytes
그대로 담았으며 `provenance.json`·`missing.json`에9슬롯의 출처와 누락2개를 표시한다.
`source-copies.json`과 원문 SHA로 결박했고 Git에는 생성 원문·비밀 파일을 추가하지 않았다.

| 파일(root 기준) | SHA-256 |
| --- | --- |
| `hard9.py` | `ae01598cbf4a829d36a5a0a033c2734ae0b065d4e3c73d251050bcc3647b28b6` |
| `prepared-inputs.json` | `123623870c4c82eb73fb813f5ce94588d51956627eaf26a16396fa7b1a4ad4f6` |
| `generation-order.json` | `e3b097d3467b85412d254176627115df6a29fd44fa66c869ffaa271c021fd3dd` |
| `evaluation-runtime-guard.json` | `f817c7772a495721073664b2ae673c9ac5a162913a48d71a40e12530c4c0c7d0` |
| `finalize_hard9.py` | `234811235452a07d4d027cee5a5c8520eaf28a671c92d91aa9af3a26d3ad50ea` |
| `final-summary.json` | `19650ddd6dd83f11476ffd81af1045f22466c067c4a84e417516f220819d7a3a` |
| `index.json` | `f00130f9e851d45a55ed452e452d6299481783dd766553f44d2cd6b6e3cc1505` |
| `source-copies.json` | `7a95d3a3d967649c5a5051722486d80b6a5bb3a6bd38f10cb49c027dc3d2ca46` |
| `hard9-original-sources.zip` | `fadd96209245c23397beaa4c636201858fd86f6d1621372465721699b1510717` |
| `resume-candidates.json` | `74e243943d61ae9ac0e1f9189af174573d50100c658293c60da9e83ee16ff54b` |
| `inference-stop.json` | `11177021d5581e6c2a4de1521cc15250e8ef25706465c5c17bb6cee9ecdaf355` |
| `vm-cleanup.json` | `3202cd0d42ae77750de9146d33bab224af1c1d790dcdcaf5b4d5db3795d3f23c` |

원문7개의 source SHA와 개별 generation/evaluation identity는 ZIP provenance·최종 요약·index에
보존한다. 기존 fixture·oracle·소스63개·이미지·endpoint guard를 재사용했고 바꾸지 않았다.
평가는 한 프로세스씩 내부 artifact 최대2개·Pine 우선으로 진행했고 완료 캐시는 재실행하지
않았다. 평가 완료 후 작업 소유 연구 VM의 활성 컨테이너0·원설정6 CPU/8 GiB를 확인하고
초기 `Stopped`로 복구했다. 공유 DB·worker·다른 VM·호스트 전원 설정 변경은0이다.

다음 명령은 API를 호출하지 않고 같은 source/identity의 완료 평가 캐시를 재사용한다.
소유권이 확인된 원설정 연구 VM에서만 실행하며 호스트 비격리 실행으로 대체하지 않는다.

```bash
set -a; . apps/api/.env.local; set +a
DOCKER_HOST=unix:///Users/woosung/.lima/qb-python-research/sock/docker.sock \
  /Users/woosung/project/agy-project/quant-bridge/apps/api/.venv/bin/python \
  runs/gemini-language-comparison/flash-sol-hard9-v1/hard9.py evaluate \
  --run-dir runs/gemini-language-comparison/flash-sol-hard9-v1 \
  --authorization-file runs/gemini-language-comparison/flash-sol-hard9-v1/quota-authorization.json
```

문서 전용 PR #927의 base는 `feat/gemini-python-generation`이다. CI의 PR base 필터는
`main`·`stage/**`이므로 `NOT_TRIGGERED`이며 job `SKIPPED`나 제품 회귀 통과로 보고하지
않는다. 문서 diff·단일 다음 행동만 검증하고 제품 전체 회귀·과거 전체 평가는 반복하지 않았다.
