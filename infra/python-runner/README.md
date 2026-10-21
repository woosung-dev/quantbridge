# 오프라인 연구용 Python 격리 이미지

사용자 Python의 웹·서버 실행 서비스는 제공하지 않는다([ADR-045](../../docs/adr/045-python-strategy-research.md)).
이 이미지는 내부 오프라인 연구 CLI에서만 사용한다. 앱 API·Celery와 연결하는 HTTP gateway와
systemd 배포 예제는 제거했다. 기존 DB·거래소 권한과 분리하며 일반 Docker/호스트 실행으로 우회하지 않는다.

1. 로컬 Linux VM의 Docker에 gVisor `runsc` runtime을 등록한다.
2. 저장소 루트에서 `sh infra/python-runner/build.sh`로 이미지를 빌드한다.
3. 오프라인 연구 CLI에만 해당 Docker endpoint를 지정한다. 앱 환경설정에는 넣지 않는다.

## macOS 로컬 VM

실측 환경은 Lima의 별도 `qb-python-research` VM이다. 공유 Docker Desktop의 runtime·context를
바꾸지 않고 호스트 디렉터리를 마운트하지 않는다. 최초 VM 생성은 다음과 같다.

```sh
limactl start --name=qb-python-research --vm-type=vz --cpus=2 --memory=4 --disk=20 --mount-none --tty=false template:docker-rootful
```

VM 안 Docker에 [공식 gVisor 설치 절차](https://gvisor.dev/docs/user_guide/install/)로 `runsc`를 등록한다.
이후 재기동은 `limactl start qb-python-research`다. 빌드·연구 CLI를 실행하는 셸에만
다음 Docker endpoint를 지정한다. 앱 `.env`나 전역 Docker context에 넣지 않는다.

```sh
export DOCKER_HOST="unix://$HOME/.lima/qb-python-research/sock/docker.sock"
sh infra/python-runner/build.sh
apps/api/.venv/bin/python tools/research/cli.py --run-dir runs/indicator-research pilot
```

이 구성은 오프라인 연구 전용이다. VM을 종료하면 로컬 Python 연구 실행이 차단된다.

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
900초 한도는 격리 전략 프로세스의 통신·실행에 적용한다. 신뢰된 제어부의 통계 후처리까지 포함한
전체 명령 시간 보장이 아니다. 서버 HTTP gateway·systemd 서비스·앱 연결 설정은 제공하지 않는다.
