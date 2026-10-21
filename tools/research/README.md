# 출처와 가설을 구분하는 로컬 지표 연구

루트에서 `apps/api/.venv/bin/python tools/research/cli.py --help`로 명령을 확인한다.
산출물은 `runs/`에만 기록하며 공유 DB·Celery·거래소 주문을 사용하지 않는다.

1. `sources`: 제공된 한국어 YouTube 6채널의 최초 공개 영상 목록 metadata를 수집한다. 페이지 변경·로그인·수집 실패는 `blocked`로 기록한다. 제목을 보고 진입·청산 규칙을 추정하지 않는다. 원본 코드 사용권과 영상 시각은 확인 전까지 unknown이다. 전체 채널 이력 수집을 주장하지 않는다.
2. `catalogue`: 공개 지표의 서로 다른 역할을 조합한 연구 가설 100개와 파일럿 10개를 생성한다. 10종 추세·가치 필터 × 10종 진입 신호이며 파라미터만 다른 복제 후보를 세지 않는다. 영상 원본 재현 100개가 아니다. EMA·RSI 등의 초기화는 최대 최근 201봉으로 정의한 유한 이력 계산이므로 특정 라이브러리·TradingView와 숫자가 같다고 주장하지 않는다.
3. `freeze --end 2026-10-21`: UTC 기준 24개월과 추가 200봉을 Bybit public linear API에서 동결한다. BTC·ETH USDT 무기한의 실제 펀딩을 포함한다. 과거 정산 간격이 현재 상품 metadata와 달라 grid가 맞지 않으면 별도 확인 전 차단한다. `validate`로 요청 기간·누락·중복·가격·펀딩·hash를 검증한다. 이 grid는 현재 주기를 과거에 적용한 `historical_schedule_assumption`이다. 관측 정산과 min/max·grid만으로 전체 과거 정산 일정이 독립 검증됐다고 주장하지 않으며 `funding_status=observed_settlements_only`를 유지한다.
4. `pilot`은 10후보 × 종목 2개 × 시간봉 3개 × 기간 2개 = 120셀을 평가한다. 모두 완료되면 `batch`로 100후보 1,200셀을 평가한다. 마지막 6개월 이전의 3·6개월 개발 창만 사용한다. 현재는 두 개발 창을 사용하며 여러 시점의 walk-forward를 수행했다고 주장하지 않는다. `journal.jsonl`의 완료·오류·timeout은 같은 hash로 중복 실행하지 않고 실행 중 중단은 재개한다. gVisor·이미지가 없으면 명시적으로 blocked이며 호스트 실행으로 우회하지 않는다.
5. `champion --candidate <ID> --symbol BTCUSDT --timeframe 4h`로 개발 임계값 통과 근거가 있는 단일 후보를 동결한 뒤 `holdout`으로 최종 3·6개월을 한 번 평가한다. 수수료·슬리피지·maker 수수료 2배 결과는 참고용이다. 기본 비용 결과 둘 다 수익 > 0·PF ≥ 1.1·|MDD| ≤ 25%·완료 거래 ≥ 30을 확인한다. 과거 구간은 `retrospective_not_untouched`이고 등록시각 문자열도 사전등록 증거가 아니다. `thresholds_passed`와 별개로 `promotable=false`를 유지한다. 새 미사용 기간과 과거 펀딩 일정의 독립 증거 없이는 검증 전략으로 서버에 올리지 않는다. 자동 배포·자동 주문은 하지 않는다.

기본 결과 설정은 10,000 USDT·레버리지 1배·단일 포지션·자본 100%·다음 봉 시가 체결이다. `requested_config`와 엔진이 반환한 `config_used`를 모두 기록한다. 데이터·코드·이미지 ID·실행기 hash로 재현 입력을 고정한다. 손실 0의 PF는 프로젝트 계약에 따라 `null`이므로 양의 실현 이익과 0 손실을 확인한 경우에만 무한대 PF로 판정한다.

연구 가설의 2% 손절·4% 익절은 진입가 대비 확정 종가에서 판정하고 다음 봉 시가에 청산한다. 봉 내부 가격 도달 즉시 체결되는 보호주문이 아니므로 갭·봉 내부 움직임으로 손실은 2%를 넘을 수 있다. 봉 내부 TP/SL은 정산 시점의 보유 여부가 미상일 수 있어 초기 시도에서 펀딩 반영 실패로 기록됐으며 그 오류 이력은 보존한다. 성공을 위해 불확실 펀딩을 0으로 바꾸지 않는다.

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

검토 묶음 내보내기는 단일 후보의 별도 기간 평가 완료 후 실행한다. 코드·API 저장 요청·네 가지 최종
결과·데이터 명세와 hash를 포함하며 CSV·비밀 설정·영상을 복사하지 않는다. 실패 후보도 검토 가능하나
수치선 통과·배포 승인을 부여하지 않는다. 기존 출력 디렉터리를 덮어쓰지 않는다.

공개 API 계약: [Kline](https://bybit-exchange.github.io/docs/v5/market/kline), [Funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate). 시세 조회는 공개 거래 데이터이며 demo 계정 주문을 실행하지 않는다.
