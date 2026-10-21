# 출처와 가설을 구분하는 로컬 지표 연구

루트에서 `apps/api/.venv/bin/python tools/research/cli.py --help`로 명령을 확인한다.
산출물은 `runs/`에만 기록하며 공유 DB·Celery·거래소 주문을 사용하지 않는다.
사용자 Python의 웹·서버 실행 서비스는 제공하지 않는다([ADR-045](../../docs/adr/045-python-strategy-research.md)).
이 문서의 명령은 내부 오프라인 연구 전용이며 서버 전략 등록·실행 경로와 연결되지 않는다.

1. `sources`: 제공된 한국어 YouTube 6채널의 최초 공개 영상 목록 metadata를 수집한다. 페이지 변경·로그인·수집 실패는 `blocked`로 기록한다. 제목을 보고 진입·청산 규칙을 추정하지 않는다. 원본 코드 사용권과 영상 시각은 확인 전까지 unknown이다. 전체 채널 이력 수집을 주장하지 않는다.
2. `catalogue`: 공개 지표의 서로 다른 역할을 조합한 연구 가설 100개와 파일럿 10개를 생성한다. 10종 추세·가치 필터 × 10종 진입 신호이며 파라미터만 다른 복제 후보를 세지 않는다. 영상 원본 재현 100개가 아니다. EMA·RSI 등의 초기화는 최대 최근 201봉으로 정의한 유한 이력 계산이므로 특정 라이브러리·TradingView와 숫자가 같다고 주장하지 않는다.
3. `freeze --end 2026-10-21`: UTC 기준 24개월과 추가 200봉을 Bybit public linear API에서 동결한다. BTC·ETH USDT 무기한의 실제 펀딩을 포함한다. 과거 정산 간격이 현재 상품 metadata와 달라 grid가 맞지 않으면 별도 확인 전 차단한다. `validate`로 요청 기간·누락·중복·가격·펀딩·hash를 검증한다. 이 grid는 현재 주기를 과거에 적용한 `historical_schedule_assumption`이다. 관측 정산과 min/max·grid만으로 전체 과거 정산 일정이 독립 검증됐다고 주장하지 않으며 `funding_status=observed_settlements_only`를 유지한다.
4. `pilot`은 10후보 × 종목 2개 × 시간봉 3개 × 기간 2개 = 120셀을 평가한다. 모두 완료되면 `batch`로 100후보 1,200셀을 평가한다. 마지막 6개월 이전의 3·6개월 개발 창만 사용한다. 현재는 두 개발 창을 사용하며 여러 시점의 walk-forward를 수행했다고 주장하지 않는다. `journal.jsonl`의 완료·오류·timeout은 같은 hash로 중복 실행하지 않고 실행 중 중단은 재개한다. gVisor·이미지가 없으면 명시적으로 blocked이며 호스트 실행으로 우회하지 않는다.
5. `champion --candidate <ID> --symbol BTCUSDT --timeframe 4h`로 개발 임계값 통과 근거가 있는 단일 후보를 동결한 뒤 `holdout`으로 최종 3·6개월을 한 번 평가한다. 수수료·슬리피지·maker 수수료 2배 결과는 참고용이다. 기본 비용 결과 둘 다 수익 > 0·PF ≥ 1.1·|MDD| ≤ 25%·완료 거래 ≥ 30을 확인한다. 과거 구간은 `retrospective_not_untouched`이고 등록시각 문자열도 사전등록 증거가 아니다. `thresholds_passed`와 별개로 `promotable=false`를 유지한다. 새 미사용 기간과 과거 펀딩 일정의 독립 증거 없이는 검증 전략으로 서버에 올리지 않는다. 자동 배포·자동 주문은 하지 않는다.

기본 결과 설정은 10,000 USDT·레버리지 1배·단일 포지션·자본 100%·다음 봉 시가 체결이다. `requested_config`와 엔진이 반환한 `config_used`를 모두 기록한다. 데이터·코드·이미지 ID·실행기 hash로 재현 입력을 고정한다. 손실 0의 PF는 프로젝트 계약에 따라 `null`이므로 양의 실현 이익과 0 손실을 확인한 경우에만 무한대 PF로 판정한다.

100개 후보는 서로 다른 규칙 조합이며 통계적으로 독립인 100개 표본이 아니다. 3개월 창도 6개월 창과
겹친다. 1,200개 개발 셀의 통과 건수는 탐색 결과이며 다중 비교를 보정한 통계적 유의성을 뜻하지 않는다.

연구 가설의 2% 손절·4% 익절은 진입가 대비 확정 종가에서 판정하고 다음 봉 시가에 청산한다. 봉 내부 가격 도달 즉시 체결되는 보호주문이 아니므로 갭·봉 내부 움직임으로 손실은 2%를 넘을 수 있다. 봉 내부 TP/SL은 정산 시점의 보유 여부가 미상일 수 있어 초기 시도에서 펀딩 반영 실패로 기록됐으며 그 오류 이력은 보존한다. 성공을 위해 불확실 펀딩을 0으로 바꾸지 않는다.
동결 카탈로그의 `-2%/+4%` 가격 요약은 롱 기준이다. 실제 소스는 롱 진입가의 98%/104%,
숏 진입가의 102%/96%로 방향을 반영한 손실 2%·이익 4%를 계산한다.

최종 기간 개봉 전에 `holdout-opened.json`을 기록하므로 오류·중단도 재선정 근거가 되지 않는다. 데이터 파일은 암호화하지 않으며 CLI 접근 제한은 연구 절차 가드다. 파일을 직접 읽거나 복사해 다른 실험으로 재사용하면 독립 최종 검증으로 인정할 수 없다. 특정 영상이 그 기간 실적을 이미 노출했다면 해당 전략은 새 미사용 기간이 필요하다.

기존 `apps/api/scripts/validate_pine_signals.py`는 검토한 공개 Pine 원본·TV native 사건·독립 Python oracle·선물 원장을 교차 검증하는 정본이다. 이 도구의 source 수집과 100개 독립 가설은 그 원본 일치 판정을 대체하지 않는다. 기존 50개 연구의 manifest·소스·참조 파일을 함께 확보하면 기존 검증기를 먼저 사용한다. source 파일이 없거나 부분 native 구간만 있는 항목은 재현 성공·독립 원본 100개에 보태지 않는다. Python sandbox 편집 실행기는 이 교차 검증 경로와 별도이며, 원본 일치용 oracle을 임의 변경해 가설 수를 늘리지 않는다.

```bash
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research sources
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research catalogue
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research freeze --end 2026-10-21
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research validate
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research pilot
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research batch
apps/api/.venv/bin/python tools/research/export_candidate.py --run-dir runs/indicator-research --output runs/indicator-candidate-review
```

검토 묶음 내보내기는 단일 후보의 별도 기간 평가 완료 후 실행한다. 코드·과거 형식의 저장 요청 자료·네 가지 최종
결과·데이터 명세와 hash를 포함하며 CSV·비밀 설정·영상을 복사하지 않는다. 실패 후보도 검토 가능하나
수치선 통과·배포 승인을 부여하지 않는다. 저장 요청 자료를 받는 Python 서비스 API는 없으며 자동 제출하지 않는다.
기존 출력 디렉터리를 덮어쓰지 않는다.

공개 API 계약: [Kline](https://bybit-exchange.github.io/docs/v5/market/kline), [Funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate). 시세 조회는 공개 거래 데이터이며 demo 계정 주문을 실행하지 않는다.

## 동일 진입 규칙의 SL·반익절·trailing 비교

`swing_exits.py`는 기존 동결 가설·데이터·최종 기간 개봉 기록을 수정하지 않는 별도 실험이다.
동일 TF 직전 완료 두 봉의 저점/고점과 실제 진입가 거리의 10% 바깥에 SL을 정하고 초기 R을
고정한다. 1.5R에서 최초 수량의 50%를 익절하고, 2R부터 진입가 BE를 시작으로 2R 거리의
trailing을 유리한 방향으로만 옮긴다. BE는 비용 전 진입가이므로 순손익 0을 보장하지 않는다.

1. `freeze`: 기존 개발 6개월(원래 최종 기간 시작 직전)만 실제 Bybit 1분봉으로 동결한다.
   공개 API 요청별 checkpoint와 hash로 중단 후 재개한다. 4h·1d의 실행을 1h·15m로 대체하지 않는다.
2. `validate`: 정확한 1분봉 grid·가격·hash를 검사하고 모든 1h/4h/1d OHLC를 재집계해 동결 부모봉과
   일치하는지 확인한다. 거래량 합의 차이는 별도 audit에 기록한다.
3. `pilot`: 기존과 같은 10가설 × 12조건 120셀에서 원본·새 청산 정책을 각각 실행한다(240회).
   원래 TF의 지표 계산은
   gVisor에서 하고 별도 1분봉 시계가 청산을 재생한다. 공유 DB·Celery·주문·호스트 소스 실행은 없다.
4. `batch`: 같은 코드·데이터·정책·이미지의 pilot 120셀 완료 후 100가설 1,200셀(2,400회)로 확대한다.
   완료·오류는 같은 job hash로 중복 실행하지 않으며 중단된 실행은 재개한다.
5. `report`: 기존 결과와 새 결과의 기준 통과·순수익률·MDD를 비교한 JSON/Markdown을 기록한다.

```bash
apps/api/.venv/bin/python tools/research/swing_exits.py --run-dir runs/swing-exits-v1 freeze
apps/api/.venv/bin/python tools/research/swing_exits.py --run-dir runs/swing-exits-v1 validate
apps/api/.venv/bin/python tools/research/swing_exits.py --run-dir runs/swing-exits-v1 pilot
apps/api/.venv/bin/python tools/research/swing_exits.py --run-dir runs/swing-exits-v1 batch
apps/api/.venv/bin/python tools/research/swing_exits.py --run-dir runs/swing-exits-v1 report
```

임의 사용자 소스를 바꾸지 않는다. 저장소가 작성한 v2 template의 position 의존 청산 절이 정확히
한 번 존재하는지 확인하고 그 절만 제거한다. 원본과 추출된 진입 소스의 hash를 함께 보존한다.
확정 부모봉 종가의 filter AND entry signal은 포지션과 무관한 동일 진입 기회이며 실제 진입 거래
수는 청산 시점 차이로 달라진다. 새 정책은 기존 close/SL/TP 신호를 무시한다. 같은 방향 신호는
기존 계획을 유지하며 실제 반대 방향 주문에서 이전 청산 계획을 취소하고 새 generation을 만든다.

비교용 baseline은 원본 source의 기존 청산 규칙을 같은 새 원장으로 다시 실행한다. 두 정책 모두
동일한 1분봉 equity·수수료·순자산 sizing·펀딩·PF 모형을 사용한다. 원본 source의 포지션 의존 판단은
보존하고 새 swing 정책은 중립 진입 source를 사용한다. 동일 부모봉 종가 샘플 MDD도 보조로 기록한다.
원본은 보유 중 반대 신호에 청산만 하고 새 정책은 조건을 만족하는 반대 진입 신호에 직접 반전한다.
따라서 성과 차이는 청산 가격뿐 아니라 반전·재진입 정책 변경도 포함한다.
이전 1,200개 결과는 원본 소스·결과 hash를 검증한 참고 자료로만 보존한다. 이전 실행기의 sizing·펀딩·PF·
해상도가 다르므로 그 스냅샷과의 차이를 새 청산의 효과로 단정하지 않는다.
반익절·잔여 청산은 같은 position episode로 집계해 거래 수 기준 30건을 부풀리지 않는다.

같은 1분봉 안에서도 실제 tick 경로는 알 수 없다. OHLC/OLHC 두 시나리오 중 비용 전 종가 평가가
불리한 결과를 고르며 모든 가능한 경로의 최악값이나 실제 체결 순서라고 주장하지 않는다.
이전 최종 기간을 다시 개봉하는 명령은 없다. 이 비교는 개발 기간을 재사용한 회고 분석이며
`promotable=false`를 유지한다. 이미 열어본 최종 기간을 후속 분석에 쓰면 반드시
`retrospective_reused_period`로 별도 표시해야 하며 새 독립 최종 검증으로 인정하지 않는다.

시간이 오래 걸리는 전체 비교는 `swing_parallel.py`로 최대 4개 프로세스에 분배할 수 있다.
동일한 16셀로 2·4 프로세스의 처리 시간을 먼저 비교하며 성적을 보고 청산 정책을 바꾸지 않는다.
원본 파일은 hardlink로 읽고 worker별 journal/results는 분리한다. 부모 프로세스만 master lock을
보유해 완료 결과의 소스·실행기·데이터·job hash와 파일 SHA를 검증한 뒤 경로를 정규화해 병합한다.
worker가 중단돼도 완결 결과는 검증 후 재사용하고 실행 중이던 셀만 재개한다. 직렬·병렬 모두
요약 숫자와 별개로 실제 pilot 120개 고유 완료 기록 및 결과 파일을 검증해야 전체 비교를 허용한다.

```bash
apps/api/.venv/bin/python tools/research/swing_parallel.py --run-dir runs/swing-exits-v3 --workers 4 --limit 16 probe
apps/api/.venv/bin/python tools/research/swing_parallel.py --run-dir runs/swing-exits-v3 --workers 4 pilot
apps/api/.venv/bin/python tools/research/swing_parallel.py --run-dir runs/swing-exits-v3 --workers 4 batch
```

각 병렬 계획에는 실행 전 orchestrator 소스 hash·프로세스 수·할당 셀·분배 방식·실험 hash를 고정한다.
기존 소스·정책·실행기를 바꾸면 같은 결과 디렉터리에서 이어 돌리지 않고 새 실험으로 분리한다.
