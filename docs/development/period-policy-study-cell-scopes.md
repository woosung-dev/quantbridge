# 기간별 지원 범위와 미실행 보류

기존 [기간별 정책 연구](./period-policy-study.md)의 기본값·준비 봉·원본당 생성 2회·격리 실행 계약을 유지한다.
특정 시간봉의 일부 기간만 적격이면 전체 시간봉을 완료 또는 보류로 뭉치지 않는다.

승인 근거는 원문·동결 입력·생성 코드·검토·격리 프로토콜의 해시와 정확한
`시간봉 × 기간 × A/B` 셀 집합이다. 준비 봉 1,000개도 판정 대상이다.
평가 구간에 신호가 없더라도 준비 봉에서 미지원 주문이 활성화되면 해당 셀은 실행하지 않는다.

기간별 승인에는 `supported_cell_scopes`, `hold_cell_scopes`, 지원 셀 수, 보류 셀 수,
문맥 증명과 원문별 범위 증명의 해시를 기록한다. 두 집합은 겹치지 않고 전체 30셀을 구성한다.
날짜형(`qualification_type` 생략 또는 `date_gate_false`)은 전체 loaded history의
`date_gate_true_rows=0`과 원본별 새 원장 무노출 귀납을 요구한다.
action형(`fixed_input_action_invariance`)의 `fresh_flat_only=true`는 초기 원장만 flat이라는 뜻이다.
이후 거래·노출은 가능하며 날짜형의 무노출 증명이나 합성 비평탄 포지션의 일반 지원으로 확대하지 않는다.

새 `run_g5a_scoped_source_v2.py`의 action형 슬롯은 `JpkdOdm9` 하나다.
원본 및 `action_invariance_audit`의 정확 SHA, 전체 15개 동결 입력 핀과 audit `cases`의 `rows`를 검사한다.
허용 pair의 `pivot_action_difference_indices`와 `raw_round9_action_difference_indices`는 모두 비어 있어야 한다.
정확한 지원은 1h P2–P5 및 4h·1d P1–P5(28셀), 보류는 1h P1(2셀)이다.
`loaded_parent_files`에는 허용 14개 pair를 한 번씩 기록하고 실제 dataset의 `file`·`sha256`·
`loaded_rows`와 `warmup_bars=1000`을 결박한다. `plans[TF].allowed_periods`도 같은 범위여야 한다.
다른 원본은 별도 슬롯 검토 없이 이 증명을 재사용하지 않는다. 기존 날짜형 v1은 불변 보존한다.

새 v3의 `fixed_input_primary_exclusivity_invariance`는 `shared_events` 원본 네 슬롯만 지원한다.
`primary_exclusivity_summary`는 원본별 감사·원문 SHA와 전체 15개 동결 입력의 해시를 결박한 정규화 요약이다.
SHA가 고정된 normalizer가 원래 audit를 다시 읽고 계산한 요약과 바이트 해석 결과가 같아야 한다.
각 허용 pair의 전체 준비·평가 구간에서 양방향 사건 0, 관련 pivot 정책의 사건 차이 0,
float/Decimal 사건 차이 0을 요구한다. 거래가 없다는 증명이 아니며 초기 원장 flat 이후 노출은 가능하다.

| 원본 | 지원 pair | 지원/보류 셀 |
|---|---|---:|
| 47SxfbN5 | 4h P2–P5, 1d P1–P5 | 18 / 12 |
| Fzdk4xFb | 1h P1/P4, 1d P1 | 6 / 24 |
| PqN9ejOj | 1d P1 | 2 / 28 |
| uI0AyMIF | 1h P1–P4, 4h·1d P1–P5 | 28 / 2 |

Pq는 기본 경로에 pivot 호출이 없어 정책 비교를 비해당으로 기록하고 수치별 사건 열을 검증한다.
uI의 원래 audit가 제공하지 않는 사건 열 SHA는 발명하지 않고 실제 차이 index 배열을 검증한다.
`selected_entry_intent_invariance_matrix`에는 후보·차이 수·원 JSON pointer와 제공되는 경우의 사건 열 SHA를 기록한다.
context proof의 `evidence`에는 원본별 scope proof, 정규화 summary, 원래 audit 핀이 모두 필요하다.
`loaded_parent_files`는 실제 허용 pair만 포함하며 v2와 같은 행 수·warmup·해시 검사를 거친다.
이 타입을 계정 피드백 원본으로 일반화하지 않는다. 날짜/Jpk형과 기존 완료 helper는 보존한다.


새 v4의 `fixed_input_feedback_projection_invariance`는 `position_feedback`인 `w2dDydN3` 한 슬롯만 지원한다.
`feedback_projection_summary`는 기존 정규화 요약의 정확 파일·SHA를 결박한다.
SHA가 고정된 `check_g5a_w2_feedback_scope_v1.py`는 원래 두 audit를 다시 읽고 전체 15개
parent 입력, native 15분 입력·manifest·독립 감사, 원문·생성 계약·수식·엔진 핀을 확인한다.
허용 범위는 1h P4와 4h·1d P1–P5(22셀), 보류는 1h P1/P2/P3/P5(8셀)이다.

두 후보(`strict_pivot`, `partial_initial_lazy_history`)마다 새 flat 원장의 준비 봉 종료 및
첫 평가 봉 callback 후 tracked ID(999/1000)가 기준과 같아야 한다.
평가 구간은 모든 SDK 방향(flat/long/short)과 내부 tracked ID(code/L/S)의 9조합에 대해
다음 action·ID의 실제 차이 배열을 검사하고, 평가 방향별 intent 차이 배열·수도 0이어야 한다.
요약의 귀납 Boolean만으로 승인하지 않으며 실제 배열·경계 ID 값과 대조한다.
준비 구간의 callback 사건 차이나 평가 score·TA·pivot·primitive 차이를 모두 없다고 주장하지 않는다.
`fresh_flat_only=true`는 초기 원장 조건이며 평가 구간의 무노출을 뜻하지 않는다.

context `evidence`에는 scope proof·정규화 요약·두 원래 audit 핀이 필요하다.
각 허용 TF의 `feeds`는 정확히 native `15` 하나이며 file·SHA·`timeframe="15"`·
`initial_closed_limit=1000`을 감사의 실제 원격 초기화와 결박한다.
`loaded_parent_files`에는 허용 11개 pair의 실제 행 수·SHA·warmup만 기록한다.
다른 원본이나 입력, 초기 포지션, 추가 수식 정책에 이 한정 귀납을 적용하지 않는다.
날짜·Jpk·공유사건 네 슬롯과 기존 helper 바이트는 보존한다.

호스트 범위 러너는 기존 worker 호출 직전에 허용 조합·문맥·파일 해시·기존 실행 흔적을 확인한다.
보류 조합에는 실행 요청·worker job·금융 체크포인트를 만들지 않는다.
성공은 완료 셀의 정확한 집합과 결과 해시가 모두 일치할 때만 기록한다.
중간 실패는 0이 아닌 종료 코드로 중단하며 자동 재개하지 않는다.
기존 worker의 직접 CLI는 기간 제한을 집행하지 않으므로 기간별 승인은 이 범위 러너로만 실행한다.

집계에서는 지원 셀 완료·지원 셀 실패·지원 셀 미시도·보류 미실행을 구분한다.
예를 들어 26셀 완료·4셀 보류는 30셀 완료가 아니다. native TradingView 동등성이나 실제 전략 등록도 별도다.

`observe_g5a_resources_v6.py`는 scoped v1/v2 모두를 금융 가족으로 분류하고 기존 자원상한을 유지한다.
`inventory_g5a_dispositions_v4.py`는 admission의 helper SHA로 v1/v2 guard를 선택해 두 qualification을 집계한다.
AST·임시 host fixture 검증은 `verify_g5a_scoped_host_guards_v2.py`이며 실제 worker·원문·생성 전략은 실행하지 않는다.
v3용 observer v7은 scoped v1/v2/v3 가족을 분류하고 inventory v5는 정확 helper SHA로 guard를 선택한다.
`verify_g5a_scoped_host_guards_v3.py`는 기존 회귀와 네 source의 정확 분할·보류 산출물 0·핀 변조 및
admission/scope/context 핀을 함께 바꾼 범위 확장 거부를 임시 host fixture로 검사한다.

v4용 observer v8은 scoped v1–v4 가족을 분류하고 inventory v6은 admission의 정확 helper SHA로
각 버전 guard를 선택한다. `verify_g5a_scoped_host_guards_v4.py`는 앞선 회귀와 w2의 정확 22/8 분할,
보류 산출물 0, 원본 감사·동결 입력·native 문맥 핀 변조 및 재핀한 범위 확장 거부를 검사한다.
이 검증은 임시 host fixture이며 실제 금융·모델·전략·격리 실행은 없다.

v5는 공유사건 타입에 `K4zaGkLy` 한 슬롯을 추가한다. normalizer v2는 기존 네 원본을
불변 v1 normalizer에 위임하고 K4의 원래 월경계 audit·추가 재심·관측 native 1M 출처 5개와
전체 15개 parent 입력을 직접 대조한다. 기본 Auto의 최종 C2 사건은 다음 월 첫 parent에서
`c2[1]`만 소비하므로, 그때 완료된 직전 두 native 월봉으로 같은 최종 사건을 계산한다.
현재 월의 미확정 H/L/C를 보내거나 원문의 lookahead를 일반적으로 고치는 승인이 아니다.
정확한 지원은 1h·4h P1/P2/P5 및 1d P1/P2(16셀), 나머지 14셀은 양쪽 C2 조건이 함께
참인 실제 witness 때문에 미실행 보류한다. `alert.freq_once_per_bar`를 bullish 우선 금융 정책으로 바꾸지 않는다.

K4의 `primary_exclusivity_summary` 및 원래 audit, `additional_evidence_pins`의 추가 재심·
native 월봉 raw/manifest/독립 감사/관측 응답/receipt를 context evidence에 모두 결박한다.
각 허용 TF의 `feeds`는 `1M` 하나이며 실제 raw SHA와 `initial_closed_limit=1000`을 요구한다.
source mode는 `shared_events`만 허용한다. v5의 observer v9·inventory v7은 앞선 버전들과
새 버전을 함께 분류하고, 신뢰 host fixture v5가 K4의 정확 8pair·보류 산출물 0 및
원천·재심·정규화·문맥·재핀 범위 확장 거부를 검사한다. 날짜/Jpk/기존 공유사건/w2 계약은 보존한다.


v6는 같은 공유사건 타입에 `bpH84GWN`(24/6셀), `kALEp0QJ`(28/2셀),
`ooO6MdvG`(8/22셀)의 구조적 슬롯을 추가한다. normalizer v3는 기존 슬롯을 불변 위임하고
각 원본의 전체 15개 입력·후보별 최종 사건·준비/평가 dual 및 원격 초기화 증거를 검사한다.
구조적 범위 증명은 원본의 최종 방향 채택이나 생성 적격 승인을 대신하지 않는다.
원본 전체의 방향 선택 미승인 또는 생성 요청 예산 소진 판정이 있으면 전체 미실행 HOLD가 우선한다.
예를 들어 oo의 BSL/SSL 관찰에 새 반전 방향을 붙이거나, w2의 구조적 22셀을 생성 실패 뒤 실행하지 않는다.

v7은 `fixed_input_flat_entry_feedback_projection_invariance` 타입의 `jrkfG0F3`(28/2셀),
`nBKnefqc`(26/4셀)을 추가한다. 기술 상태와 사설 cooldown은 SDK와 독립적으로 갱신하고,
실제 SDK flat에서만 진입하며 명시 close가 없는 원문 구조를 검증한다.
허용 pair의 전체 준비·평가 사건과 SDK 방향×추적 ID 투영의 action/다음 ID 차이는 모두 0이어야 한다.
원문 원장·신호를 공유사건 타입으로 바꾸거나 합성 비평탄 시작을 일반 승인하지 않는다.
jrk의 보류는 1h P4, nBK의 보류는 1h P1/P2이며 각 pair의 A/B 두 셀을 함께 보류한다.

v7의 `fixed_input_shared_event_policy_invariance`는 `VrHFkq4P`(28/2셀),
v8은 같은 타입에 `beNtBrn6`(28/2셀)을 추가한다. Vr의 1h P4 및 be의 1h P1은 실제
후보별 최종 사건이 달라 보류한다. 사설 pivot·float 전체가 같다는 주장 대신 최종 사건 열과
전체 후보쌍·warmup/평가 경계를 결박한다. be는 8후보, Vr은 4후보의 원래 행렬을 검사한다.
기존 타입과 다른 `qualification_summary` 핀을 사용하며 일반 shared 원본으로 확대하지 않는다.

v9는 기존 `fixed_input_primary_exclusivity_invariance` 타입에 `d62jNtUW`만 추가한다.
지원은 1h P1/P2, 4h P1–P5, 1d P1(16셀)이고 나머지 14셀은 미실행 보류다.
normalizer v6는 정확 SHA의 기존 normalizer v5에 이전 슬롯을 위임한다. 새 원본은 실제
4후보의 전행 Boolean 열, long/short/dual index, 사건 해시, 전6후보쌍의 차이 배열 및
단계별 witness를 직접 대조한다. native 5/15/60분 전체 intrabar 배열과 초기 완료1000개는
각 parent의 연속 누적 delta 및 pivot 중심 raw H/L 샘플링 계약에 결박한다.
원문 regular Bull/Bear alert 341/342와 기본 showDiv=true/showHidden=false도 고정한다.

v6–v9에 대응하는 observer v10–v13은 새 scoped 실행을 기존 금융 가족으로 분류하고,
inventory v8–v11은 admission의 정확 helper SHA에 해당하는 guard로 검증한다.
최신 host fixture v9는 기존274개와 새37개, 총311개의 범위·변조·미실행·회귀 검사를 수행한다.
fixture 성공은 실제 전략 실행이나 native TradingView 검증을 뜻하지 않는다.
rawfloat 생성 코드가 round9/Decimal 후보 감사에만 결박돼 있으면 추가 최종 사건 감사를 요구한다.

같은 원본을 새 namespace에서 재심할 때는 원본 수와 요청 예산을 늘리지 않는다.
현재 namespace assignment는 G5A 749원본 중 DMy 한 ID만 지정 PF 공간으로 교체하며,
옛 공간의 HOLD는 역사적 namespace 판정이다. 현재 분모는 749원본·22,470논리셀이다.
현재 namespace 집계 v8은 정확 inventory v15·assignment·과거 요청 예산 SHA만 허용한다.
전체 namespace의 과거·신규 요청을 합쳐 원본당 2회를 집행하고, 미승인 namespace와 경로 탈출을 거부한다.
G1 등 새 namespace가 생기면 그 승인된 별도 원본 집합을 반영한 새 집계 버전이 필요하다.


v10은 jr/nBK/Vr/be 네 원본의 qualification 증거 누락을 새 승인 버전으로 보강한다.
기존 runtime context-v1·admission-v1·code-review·선택 코드·생성 상태의 바이트는 보존한다.
새 qualification-supplement-v2에는 기존 문맥에서 빠졌던 해당 선택 코드와 생성 상태의 정확 2핀만
추가한다. admission-v2는 원래 범위·runtime proof를 유지하고 보호된 v1 승인과 보강 proof를 참조한다.
activation receipt가 없으면 금융 진입을 거부하며, 적용 전 금융·dispatch·queue-start 흔적이 없어야 한다.
이 보강은 원본 수나 원본별 모델 요청 예산을 늘리지 않는다.

새 guard는 qualification 검사에서만 원래 evidence와 정확 2핀의 합집합을 사용한다.
실제 worker에 반환하는 runtime proof는 원래 v1 그대로이며, dispatch 전후에 v1/v2·보강·activation
핀을 모두 검사한다. inventory v12와 해당 coordinator는 지정 네 ID만 v2 승인으로 해석한다.
다른 ID의 임의 v2, 추가 정책·범위·runtime plan 변경, 세 번째 추가 핀 및 경로 탈출은 거부한다.
observer v14는 이 새 금융 가족을 기존 상한 안에서 분류한다. host fixture v10은 기존311개와
새42개, 총353개의 임시 검증으로 이 분리·핀 보호·범위·미실행 조건을 검사한다.

v11은 `fixed_input_shared_event_policy_invariance`에 `VKsBoc2g` 한 원본을 추가한다.
1h P1/P4의 피벗 동률 정책에 따른 실제 평가 사건 차이 때문에 4셀을 미실행 보류하고,
나머지 26셀만 허용한다. normalizer v7은 전15 입력의 8후보·28후보쌍을 사건 index와
해시에서 재검산한다. 같은 피벗 정책 안의 수치 후보 불변과 피벗 정책 사이의 차이를 구분하며,
사설 수치 상태 전체의 동등성을 주장하지 않는다. 원문·선택 코드·생성 상태·원본별 검토·
전체15 raw 입력 핀이 문맥 증거에 필요하다. 다른 원본은 정확 SHA의 guard v10에 위임한다.
observer v15·inventory v13은 v11을 인식한다. host fixture는 기존353개와 새40개, 총393개다.

실행 조정기를 교체할 때 이미 시작한 금융 자식은 완료 경계까지 유지한다.
완료 원본을 건너뛰려면 원래 계획·시작 승인·정확30개 완료 checkpoint와 각 결과의 실제 SHA를
고정한 인계 영수증을 시작 전과 건너뛰기 직전에 검증한다. 부분 완료를 전체 완료로 간주하거나
원래 계획의 다른 원본을 함께 건너뛰지 않는다. 미시작 대기 조정기는 시작 기록과 금융 자식이
모두 없음을 확인한 뒤 교체하며, 기존 파일과 완료 결과를 보존한다.

v12는 `fixed_input_reachable_id_feedback_projection_invariance` 타입으로 `lGXPh60w` 한 원본을 지원한다.
1h P4의 실제 피벗 정책별 action/ID 차이 때문에 2셀을 미실행 보류하고 나머지 28셀만 허용한다.
normalizer v8은 전15 raw 입력과 8후보의 확장 행렬 346,672행을 다시 읽는다. 원문 순서의
Long/Short close → Long entry → 후속 close와 도달 가능한 ID(code/Long)를 3 SDK 방향에
각각 투영하며, 모든 허용 pair의 action·다음 ID 및 준비 경계 999/1000을 검사한다.
전체 private TA 동일성이나 다른 원본의 ID 집합으로 일반화하지 않는다. 각 TF의 문맥은
raw native120 하나와 초기 완료1000개로 제한한다. observer v16·inventory v14가 새 guard를
인식하며, host fixture는 앞선393개와 새43개, 총436개다. namespace fixture v7은74개다.
이 fixture 성공은 전략 실행·native TradingView 검증·실제 등록을 뜻하지 않는다.

v13은 `fixed_input_capacity_feedback_primitive_invariance` 타입으로 `AzGi4Rwo` 한 원본을 지원한다.
1h P1의 실제 피벗 정책별 사건 차이 때문에 2셀을 미실행 보류하고 나머지 28셀만 허용한다.
normalizer v9는 전15 입력의 8후보·346,672행에서 용량 제한 전 사건, 세션 초기화,
close_all을 다시 검사한다. 카운터 0/1/2·추적 ID·사건·초기화·close_all·동일 SDK 방향의
324개 전이 관계로 임의의 동일 SDK 일정에 대한 귀납 근거를 고정한다. 고정 포지션 표본의
일치만으로 일반화하지 않는다. 각 TF 문맥은 raw native15와 초기 완료1000개로 제한한다.
observer v17·inventory v15가 새 guard를 인식하며, host fixture는 기존436개와 새377개,
총813개다. namespace 집계 v8의 fixture는74개다. 앞선 guard와 네 원본의 v2 승인 해석을
그대로 유지한다. 실제 격리 protocol 통과와 별도 승인 전에는 금융 실행을 허용하지 않는다.

`1ulzceoX`의 `fixed_input_shared_event_policy_invariance`는 scoped14와 normalizer10을 사용한다. 기본 Long 최종사건의 8개 수치·피벗 후보를 15개 입력 전체에서 대조해 1h/P4와 4h·1d 전기간 22셀만 허용하고 1h/P1·P2·P3·P5의 8셀은 실행하지 않는다. 원격 feed는 비어 있으며 내부 점수·수치 상태 전체 동일은 주장하지 않는다. 검증 범위는 851개 host fixture·74개 namespace fixture와 고정15의 43,334행 정규화 계약이다. scoped13 이전 위임과 기존 4개 v2의 scoped10 resolver는 보존한다. BP/K4의 기존 scoped3 연결 오류는 별도 보충승인 수리 대상이며 이 fixture 통과로 그 승인까지 유효하다고 판단하지 않는다.

BP/K4의 기존 scoped3 연결은 소비 후 수정하지 않는다. root가 정확 두 원본의 보충 승인 v2와 적용 영수증을 봉인하고 scoped15로 검증한다. BP의 24/6·K4의 16/14 범위 및 worker가 읽는 원래 context·code-review 바이트는 유지한다. BP의 원래 독립산술 helper·공통 CSV reader·재심 증거 3핀만 qualification 검증용 복사본에 추가한다. worker에는 원래 runtime proof를 반환한다. 기존 4개 v2는 scoped10 resolver에 그대로 위임하며, namespace10은 inventory17과 scoped15를 정확 SHA로 고른다(CLI 산출물 이름의 v8 접두사는 구형 호환 표기다). 승인 연결은 새 교정 57개와 namespace 74개 검사로 검증하며 추가 모델 요청·전략 재실행·금융 실행을 만들지 않는다.

독립 host fixture 119개를 검증하는 scoped16은 `biSRGk4f`에만
`fixed_input_recursive_private_cost_feedback_invariance`를 적용한다. 허용 범위는
1h P3/P4, 4h P1/P2/P5, 1d P1–P5의 20셀이다. 보류 10셀 중 P3/4h의 2셀은
명시한 동일 SDK 일정에서 사설 비용 비교의 수치 후보에 따라 close/hold가 갈리고,
나머지 1h P1/P2/P5·4h P4의 8셀은 유한 상태 탐색이 미종결이다. 이 둘을 실제
A/B 금융 도달 반증이나 금융 실패로 바꾸지 않는다.

원문 비용은 SDK 평균가격이 아니라 flat 진입 시 C로 초기화하고 OVS2 호출 뒤
`(old_cost + C) / 2`로 갱신하는 사설 상태다. guard는 4개 수치 후보의 전15 입력 제어열,
정확 10개 완주 비용 상위집합, 과거 lower-stop에 대한 원가격 분할, 소스·선택·상태·전체
15 raw SHA를 결박한다. `fresh_flat_only=true`는 초기 원장의 flat을 뜻하며, 모든 봉이
무노출이라는 뜻이 아니다. 원문 부호 있는 SDK 수량의 정확 `==2` 비교와 ID별 close,
동방향 entry 후 비용 변경 및 뒤따르는 close 순서는 유지한다.

observer20·inventory18·현재 namespace wrapper11은 scoped16을 인식하는 새 버전이다.
다른 원본은 정확 SHA의 scoped15에 위임하므로 BP/K4의 v2 resolver와 앞선 계약을 보존한다.
고정 범위 밖 cell/job/dispatch 흔적, 중복 실행, 미완료 뒤 자동 재개, 원본 전역 모델 요청
2회 초과를 거부한다. 앞선 908개 검사의 정확한 근거를 재사용하며, 실제 source protocol과
금융 입학은 별도다. 코드·원문을 호스트에서 실행하지 않았고 native 검증도 아니다.

금융 입학의 근거 목록은 worker가 검사하는 연구 namespace 내부 상대경로만 사용한다.
연구 폴더의 신뢰 수식 helper를 참조할 때는 원래 경로·SHA를 메타데이터에 남기고 동일한
바이트의 namespace 내부 snapshot을 근거로 결박할 수 있다. MME/LVy의 잘못된 외부 상대경로
승인은 금융 cell/job 0에서 거절됐다. 실패한 proof·helper·review는 보존하고, 사용 전 승인의
원래 바이트를 SHA 이력에 보관한 뒤 새 v2 proof·버전 승인·현재 포인터로 보충했다. 최종
승인본은 게시 전에 임시 namespace에서 실제 worker.admit의 전 TF 검사를 통과해야 한다.

biSR 전용 입학은 대표 1h P4·4h P5·1d P5에서 flat/long/short/cycle/long_size2의
full·repeat·prefix 45세션을 요구한다. proof·code-review·admission의 최종 바이트를 먼저 만들고,
임시 namespace에서 정확 scoped16과 기존 worker.admit를 통과시킨 뒤 실제 파일을 게시한다.
RUN 밖의 신뢰 산술 helper는 SHA를 검증해 `trusted_study_helper_pins` 메타로 분리하며,
worker가 RUN 안에서 검사하는 evidence에 `../../` 경로를 추가하지 않는다.

판독기 v6 초안은 v5의 곡선 환경·recipe·원장·metric·이전 PASS 재사용 검사를 유지하고,
`checked`가 같은 불변 파일의 SHA를 반복 계산하는 부분만 캐시한다. 최초 1MiB 단위 해시의
전후 stat과 dev/ino/size/mtime_ns/ctime_ns를 고정하며, 같은 파일의 상충 SHA나 메타데이터
변경은 거부한다. 출력 직전에 모든 캐시 파일과 원래 상대경로의 결박을 다시 확인한다.
v5 proof는 기존 앵커·환경 검사 아래 유효하고 v6은 같은 증거 형식의 상위 판독 버전이다.
곡선 payload를 해시 캐시에 넣지 않으며, 실행 중인 v5를 중지하거나 수정하지 않는다.
이 초안의 작은 파일 fixture는 전체 판독 성능 측정이나 실제 reader 실행을 대신하지 않는다.

현재 승인경로 감사 v4 초안은 namespace 내부 evidence와 외부 검증용 메타데이터를 구분한다.
snapshot 없는 study helper 메타는 biSR/kALE/d62/DMy 네 원본만 허용한다. biSR/DMy의
필수 helper는 정확 SHA의 scoped16/17에서 `HELPER_PINS` literal을 AST로 읽어 대조하며,
guard 코드를 import하거나 실행하지 않는다. DMy는 지정 current namespace assignment와
`FOLLOWUP_PINS`의 공통 reader 한 개를 별도 followup 메타로 검증한다. 과거 예산·정확 두
요청·guard 채택·원장 구현 핀도 메타로 분리하고 RUN 내부 evidence의 경로 경계를 완화하지 않는다.
입학 파일·현재 승인·proof의 직접 경로/SHA 결박과 기존 26원본의 error 필드 예외는 유지한다.
감사 v5는 guard10의 jrk/nBK/Vr/be 네 교정과 guard15의 bp/K4 두 교정만 정확한 v2 입학 경로로 선택하며,
해당 v2가 없으면 옛 v1으로 후퇴하지 않는다. 나머지 원본의 현재 경로는 v1이고 v4 메타 검사는 그대로 유지한다.


v17은 지정된 DMy 현재 PF namespace에서만 이중 엔진의 20지원·10보류 범위를 허용한다.
기본 namespace는 불변 v16에 위임하며 기존 DMy HOLD는 과거 판정으로 보존한다.
8개 수치 후보와 전체 15입력의 primitive·SDK/ID 전이·999/1000 경계를 검증하고,
매 dispatch 전에 원천·승인·원본 합산 2요청을 다시 확인한다. 파생 전행 검증의 프로세스 내 재사용은
동일 proof와 모든 원천 SHA 재검사가 통과한 경우에만 허용한다.

후속 대기열의 선행 완료 조건은 승인된 지원 셀 수와 같은 종류의 완료 요약을 사용한다.
부분 TF 지원 20셀은 partial summary의 20완료·10보류 상태로 이어지며 full30 완료를 기다리지 않는다.
이미 실행 중인 경로는 유지하고, 아직 시작하지 않은 독립 경로만 새 불변 계획으로 대체한다.
대체 경로는 이전 경로의 잘못된 gate가 활성화되지 않았음을 시작 직전에 재확인한다.

검산기 v7 초안은 리뷰의 선택적 `source_file` 누락을 금융 실패로 취급하지 않는다.
catalogue의 단일 ID와 정확 `sources/<ID>.pine`, 원문 수집 receipt, review·status·proof의
원문 SHA 및 review/status 바이트 핀을 함께 대조한다. 리뷰에 경로가 있으면 canonical과
정확히 같아야 하며 proof의 원문·receipt 핀도 필수다. 기존 v6의 SHA 캐시·곡선 환경·
원장·지표·prefix·실제 복원 앵커 검사는 유지하고 이전 판독기 v3–v7의 같은 증거 형식을 허용한다.
이 보완으로 과거 실패 판독본을 수정하거나 부분 성공을 전체 PASS로 승격하지 않는다.
v8 초안은 같은 경로 결박에서 리뷰 ID의 두 정식 schema(`publication_id` 또는 `id`)를
지원한다. 최소 한 키가 있어야 하고 존재하는 모든 ID 값이 정확히 같아야 한다.
v7은 보존하며 곡선 검사는 바꾸지 않는다. 실제 metadata 전체에 새 helper를 적용한
사전 검증과 자원 실측을 통과하기 전에는 실제 판독기 채택으로 간주하지 않는다.

G5에서 G1으로 넘어가기 전에 기본 namespace 7,092셀과 지정 DMy namespace 20셀의
완료·독립 지표·곡선 검산, 749원본 분할·출처·원천 보존 감사를 불변 증거로 봉인한다.
봉인기는 정확 지원 셀 집합과 보류 15,358셀의 무실행, 원본 합산 2요청, namespace 실제
경계와 필수 메타데이터·곡선 조상 핀을 대조한다. 진입과 출력 직전에 G1 namespace 부재를
확인하며, 봉인기 자체의 새 실행 0회와 G5 누적 완료 실적을 구분한다.
G1 착수 뒤에는 G5 봉인의 모든 핀 보존·G1 새 근거·949원본 전역 요청 원장을 별도로
검증한다. G1을 모르는 소비된 G5 guard나 namespace 열거기를 다시 실행하지 않는다.

전역 생성 예산은 과거 canonical 요청과 모든 승인 namespace의 실제 `request.json`을
원본별로 합산한다. 정식 `status-history`의 SHA 파일명·원본ID·완료상태는 별도 metadata로
검증하며 요청 횟수나 예산 초기화 근거로 사용하지 않는다. 이 폴더의 요청 은닉·중첩·
symlink와 무단 namespace는 거절하고, 출력 직전에 요청 집합과 경로 경계를 다시 확인한다.

최종 분류 inventory12는 기본 7,092셀과 지정 NS 20셀의 정확 완료 근거를 확인한 뒤에만
금융 예약을 0슬롯으로 해제할 수 있다. 실제 금융 worker와 자손·컨테이너도 0이어야 하며,
새 observer21 관측에 추가 3GiB를 더해 전체 6GiB 이내일 때만 한 번 실행한다.
G1 부재와 마감 근거를 실행 전후 재확인하고 정확 inventory 자식의 peak RSS·종료 코드를
성공·실패 모두 보존한다. 사전 예약량과 실제 전체 검증의 메모리 실측을 구분한다.

정확 protocol bundle의 repo-global `checked_pins`는 과거 별칭 12개를 component별로
검사해 canonical 경로로 연결한다. 원문 9,945경로 근거와 실제 고유 파일 9,938개·중복7군을
구분하며 원장 bytes는 바꾸지 않는다. 절대경로·repo탈출·symlink·비정규파일·같은 대상의
상충 SHA는 거절한다. 이 호환 처리는 namespace 내부 evidence의 `..` 금지를 완화하지 않는다.

G1은 G5 최종 봉인 뒤 별도 `g1` namespace에서 기존 Python 수리 102원본만 처리한다.
과거 요청은 원래 canonical 위치의 SHA 참조로 보존하고 새 generation 트리에 복사하지 않는다.
각 원본은 역사 요청 1회를 포함해 전체 2회가 상한이며, 새 요청은 attempt1 한 번만 허용한다.
타임아웃·실패도 요청으로 세고 재호출하지 않는다. 원문·기본 입력·방향·공통 단일 action
투영을 유지하며, 단순 오류 수정으로 정당화할 수 없는 주문 우선순위나 외부 문맥은 보류한다.
원문과 과거 선택 코드의 새 검토, 새 코드 검토와 gVisor 증거가 없으면 금융 실행하지 않는다.
G5에서 소비한 SDK·전송·엔진 파일은 수정하지 않고 필요한 G1 실행 경계는 새 버전으로 만든다.

G1의 기존 선택 바이트 재사용은 새 생성으로 세지 않는다. 원래 요청 모델·생성 시각·코드 SHA와
canonical 요청을 보존하고, 현재 검토의 실행 문맥 hash는 과거 생성 문맥과 구분한다.
고정15에서만 비노출인 일반 입력 결함은 그대로 명시한다. 날짜·세션의 전 준비/평가 입력에서
진입이 차단되는 부분 범위는 fresh-flat의 진입0→포지션0→조건부 청산0 귀납을 요구한다.
가상 비평탄 SDK에서 청산이 발생할 수 있다는 사실을 숨기거나 전체 SDK의 hold로 승격하지 않는다.
부분 지원 밖의 셀·job·dispatch는 만들지 않는다.

준비봉의 불확실한 초기 계산을 평가기간의 사건 불변과 합치지 않는다. 한정된 후보 집합의
평가 사건이 같아도 전체 준비 신호나 native 동등성이 확인된 것은 아니다. 제한 입학에는
준비 주문의 queue 부재뿐 아니라 준비 event ID의 저장과 평가 ID의 분리, entry-driven 사설 상태·
SDK 의존 부재를 확인해야 한다. 해당 원본에 요구된 전15 전행의 실제 선택 코드 대조도 별도로
완료한다. 이 근거 없이 기존 전체 입력 불변 입학틀을 재사용하지 않는다.

기존 BTC 시장 문맥은 고정된 facts의 동일 원본 target·원문 SHA·역사 결정의 직접 계보를 확인한
경우에만 계승할 수 있다. 당시 UTC 연구가정과 실제 거래소/native 시간대 실측은 구분한다.
같은 cohort의 다른 원본으로 승인을 자동 확대하거나 새 상품 메타데이터·시장 API를 추가하지 않는다.

G1의 자원 예약은 `observe_g1_resources_parallel_v6.py`를 따른다. 금융 가족마다 기본1.75GiB에
해당 입학 근거의 최대 증거 파일 크기를 더하고, 시작 예정 원본도 실행 전에 같은 방식으로
예약한다. 큰 증거의 본문은 관측기에서 읽지 않으며 실제 SHA 검증은 동결 실행·검산기가 한다.
같은 원본의 중첩 worker는 한 가족이고 독립 중복 가족은 거절한다. 전체6GiB·최대3가족과
VM2GiB 여유는 유지한다. 다른 실행의 추가 예약량도 그대로 더하며 실제 종료 뒤에만 해제한다.
저장 지표 검산은 기본512MiB, 곡선 검산은 기본2GiB에 대상 범위의 최대 증거 파일 크기를
추가한다. 프로토콜·생성의 추가2GiB는 유지한다. 예약량은 실제 동시 peak를 측정한 값이 아니다.

eESl·uq·XH·NaOX의 금융 계산은 각각30셀 완료·실패0·worker 종료0이지만 개별 RSS 감사 실패가 있다.
NaOX·Myu 입학의 원래 RSS 감사 실패와 이후 저장 근거만 재검산한 성공도 별개로 보존한다.
전체 자원 receipt를 열거해 금융4건·입학2건을 확인하며, 고정된 과거 시간 보고의 누락은 새
정정 근거로 연결한다. Myu 입학은 원4문서를 재게시하지 않고 별도2GiB에서 저장핀과
원worker3의15쌍 입학 검증만 다시 확인한다.
과거 실패 receipt를 소급 PASS로 바꾸거나 이를 이유로 전략을 재실행하지 않는다. 해당 구간의
전체 동시 peak를 사전 관측만으로 확정하지 않으며 최종 보고서에서 금융 계산 실패와 구분한다.

G1의 정확5원본(eoKh4Pay·AWa1tWoJ·82pXmSHs·D2UwK8lK·yK5180DE)은 소비된
canonical review의 status enum만 `ready` 별칭으로 연결한다. source·매핑·기본값·선택코드·
요청·원 worker3/runner2의 SHA는 바꾸지 않는다. 별칭은 canonical과 status 한 필드만 다름을
검증하며, 실제 진입점 wrapper2·qualification·별칭·canonical review 네 핀을 금융 request와
worker receipt의 extended implementation에 추가한다. observer6는 정확 wrapper1/2의
finance/worker 모드만 금융 가족으로 분류한다. 저장 검산기3도 이5원본에 한해서 네 추가핀을
엄격 대조하고, 수치 함수·원장 복원·캐시·DAG 검증은 유지한다. 과거 enum·STDOUT 실패는
실제 worker/금융 시작 전 실패로 보존하며, 수정본의 통과로 과거 기록을 바꾸지 않는다.

긴 입력의 원본별 격리 검사는 금융 런타임과 같은900초 상한을 명시할 수 있다. 동결P4
격리 함수의 두timeout 인자만 변경하고 역AST 대조로 나머지 함수가 같음을 검증한다.
runsc·network none·read-only·1GiB·1CPU·실제 컨테이너 삭제 확인은 유지한다. b9의
120초 실패에서는 완료23세션의 입력·프로필·사건SHA를 검증해 재사용하고, 미완료4세션만
900초로 실행한다. 원실패·기존세션·재개1회 claim은 별도 불변 근거로 보존한다.
