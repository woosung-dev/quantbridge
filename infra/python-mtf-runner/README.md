# 동일 BTC 시간봉 연구 실행기

기존 `python-runner` 이미지를 base로 사용하고 진입점만 별도 이미지에 추가한다.
기존 이미지 태그·ID와 금융 엔진은 변경하지 않는다. 제품 API·Celery·주문과 연결하지 않는다.

`RESEARCH_BASE`에는 별도 연구 VM에서 ID를 확인한 기존 로컬 이미지 태그를 전달한다.
빌드 전후 base ID를 대조하며 출력 이미지는 `quantbridge-python-mtf-runner:research-v1`처럼
별도 태그로 보존한다. 실행 시에는 태그 대신 실제 이미지 ID를 고정한다.

```sh
docker image inspect --format '{{.Id}}' quantbridge-python-runner:local
docker build --build-arg RESEARCH_BASE=quantbridge-python-runner:local \
  -f infra/python-mtf-runner/Dockerfile -t quantbridge-python-mtf-runner:research-v1 .
docker image inspect --format '{{.Id}}' quantbridge-python-runner:local
docker image inspect --format '{{.Id}}' quantbridge-python-mtf-runner:research-v1
```

실행 경계는 기존 `DockerPythonTransport`의 runsc·네트워크 없음·읽기 전용·1CPU·1GiB·900초를
그대로 사용한다. `tools/research/mtf_v1/transport.py`가 `ctx['market']`에 확정된 원격 OHLCV delta와
부모 시작이 속한 구간의 알려진 시가·시각만 제공한다. 원격 지표 계산과 생성 소스 실행은
컨테이너 안에서만 수행한다. 부모 `history`에는 원격 피드를 누적하지 않는다.

callback의 키는 `bar`, `history`, `position`, `params`, `market`이다. 원격 피드는
`ctx['market']['feeds'][key]`로 읽는다. 최상위 `ctx['feeds']` 별칭은 없다.
같은 시간봉에는 추가 과거 seed를 주지 않는다. 일·주·월봉도 원시 관측 데이터와 달력 종료
시각으로 확정 여부를 판단하며, 미확정 마지막 봉의 H/L/C/V를 노출하지 않는다.

`worker.py`는 사용자 선택 publication·원문/매핑/생성·원본별 요청 예산·시간봉별 입력·독립
검증·이미지·구현 SHA를 확인한다. 기존 금융 엔진의 `transport_factory`에 명시적으로 이
전송을 주입하며, 기존 언어 실패 적격 판정으로 위장하지 않는다. A/B 정책·분봉 체결·비용·
펀딩·곡선 복원은 기존 공통 엔진이 소유한다. 금융 성공은 TradingView native 검증이 아니다.

원시 전송의 전략 없는 회귀 검증:

```sh
python -m unittest tools.research.mtf_v1.test_feeds -v
```
