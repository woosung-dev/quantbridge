# Python 전략 격리 실행기

앱 API/Celery 는 HTTP client 만 사용한다. 이 gateway 와 Docker daemon 은 전용 Linux
호스트 또는 별도 Linux VM 에 둔다. 사용자 소스는 `runsc` 컨테이너의 stdin 으로만
전달하며 시세 파일·Docker socket·DB·거래소 키를 마운트하지 않는다.

1. Linux Docker daemon 에 gVisor `runsc` runtime 을 등록한다. 이름만 등록하고 실행이
   불가능한 경우도 `/healthz` 실제 초기화 검사가 실패한다. `runc` 대체 실행은 없다.
2. 저장소 루트에서 `sh infra/python-runner/build.sh` 로 이미지를 빌드한다.
   Python base 는 `mise.toml` 에서 읽는다. 수동 빌드는 `--build-arg PYTHON_BASE` 가 필수다.
3. 32자 이상 무작위 토큰을 `/etc/quantbridge/python-runner-token` 에 저장한다.
   `qb-runner` 만 읽을 수 있게 하고 같은 값을 앱의 실행기 설정에 넣는다.
4. `apps/api` 에서 `uv run python -m src.strategy.python_runtime.gateway --token-file /etc/quantbridge/python-runner-token` 로 실행한다.
   systemd 예제는 이 디렉터리의 unit 이다. 기본 바인딩은 localhost 이고 동시 실행은 1개다.
5. 인증된 `/healthz` 가 `available: true` 를 반환하는지 확인한 뒤 앱에서 사용한다.
   다른 호스트에서 연결할 때는 사설 터널 또는 TLS 종단을 사용한다.

## 전략 계약

`init(params) -> dict` 는 선택이고 `on_bar(ctx, state) -> dict` 는 필수다.
`ctx` 는 현재 확정봉 `bar`, 과거부터 현재까지만 있는 `history`, 브로커가 관리하는
`position`, `params` 를 갖는다. `bar` 는 `index`, ISO UTC `timestamp`, 문자열
`open/high/low/close/volume` 이다. `position` 은 `direction`, 절대 수량 `size`,
`average_price` 이며 미보유 시 `flat`, `"0"`, `None` 이다.

```python
def init(params):
    return {}

def on_bar(ctx, state):
    if len(ctx["history"]) < 20:
        return {"action": "hold"}
    closes = [float(bar["close"]) for bar in ctx["history"][-20:]]
    if closes[-1] > sum(closes) / len(closes):
        return {"action": "long"}
    return {"action": "close"}
```

출력 `action` 은 `hold|long|short|close` 중 하나다. 선택 `stop_loss` 와
`take_profit` 은 절대 가격 문자열이다. 수량과 손익을 전략이 지정하지 않는다.
같은 방향 신호는 포지션을 추가하지 않고 반대 방향은 기존 브로커의 반전 체결을 쓴다.
신호는 다음 봉 시가에 체결되며 마지막 봉 신호는 체결되지 않는다. 진입 신호의
브래킷은 다음 시가 진입 직후부터 활성화하고 같은 봉 SL/TP 동시 도달 시 SL 을 우선한다.
워밍업 봉도 전략에 전달하지만 해당 신호와 성과는 평가에서 제외한다.

고정 라이브러리는 이미지의 numpy/pandas 이고 타입은 `quantbridge_sdk` 로 import 한다.
실행 중 패키지 설치는 지원하지 않는다. 사용자 print 는 버린다. 프로토콜 출력 초과,
예외·잘못된 신호·900초 초과는 전체 실행 실패이며 부분 성과는 보존하지 않는다.
900초 한도는 격리 전략 프로세스의 통신·실행에 적용한다. 공통 통계 계산은 신뢰된
gateway 프로세스에서 후처리하므로 전체 요청의 엄격한 900초 한도는 아니다.
후처리 중 취소하면 결과를 폐기하지만 진행 중인 통계 계산은 완료 후 종료한다.
systemd 예제의 `CPUQuota=100%`, `MemoryMax=2G` 는 이 신뢰된 컨트롤러도 제한한다.
전체 요청을 지정 시각에 강제 종료하려면 별도 컨트롤러 프로세스 감독이 필요하다.

## HTTP 계약과 재현

Bearer 인증 `POST /v1/backtests` 에 UUID `job_id`, `source`, `bars`, `funding`,
`params`, `config`, `warmup_bars` 를 전달한다. 봉은 최대 50,000개이며
`bars` 는 `timestamp/open/high/low/close/volume`, `funding` 은 `timestamp/rate` 이다.
취소는 `POST /v1/backtests/{job_id}/cancel` 로 한다. 제출보다 먼저 온 취소도 보존하고
실행 중이면 컨테이너를 종료한다. 다른 작업 실행 중에는 503, 재사용 ID 는 409다.

결과는 `metrics`, `trades`, `equity_curve`, `config_used`, `provenance` 이다.
금융 값은 Decimal 문자열이며 provenance 에 소스·데이터·파라미터·엔진 코드·실제 이미지
ID 해시를 넣는다. 이미지 태그가 바뀌어도 해당 실행은 시작할 때 고정한 이미지 ID 를 쓴다.
펀딩 비율만으로 과거 정산 일정의 완전성을 입증할 수 없으므로
`funding_data_incomplete=None` 은 미검증이고 성공 판정의 증거가 아니다.
