# 공통 전략 실행용 Pine 격리 이미지

`run_code_backtest(..., language="pine")`는 앱의 `pine_v2` 해석기 원본을 이 이미지에서 실행한다.
호스트 해석기로 대체하는 경로는 없다. 내부 Pine broker를 실행하지 않고 외부 확정 포지션을
주입해 entry/close 의도만 반환한다. 기존 제품의 다른 Pine 실행 경로는 이 변경의 범위 밖이다.

```sh
DOCKER_HOST="unix://$HOME/.lima/qb-python-research/sock/docker.sock" sh infra/pine-runner/build.sh
```

빌드는 Python 버전을 `mise.toml`, 모든 직접·전이 의존 버전을 `apps/api/uv.lock`에서 읽는다.
이미지에는 `apps/api/src`만 복사하며 `.env`·연구 산출물·호스트 볼륨을 전달하지 않는다.
컨테이너 내부에서 설정 검증용 임의 더미 키를 생성하며 실제 키를 사용하지 않는다.
AST 디스크 캐시도 사용하지 않는다. 이미지 재빌드 후에는 이미지 ID와 소스 해시를 다시 동결한다.

Python/TypeScript와 같은 `DockerPythonTransport`를 사용하므로 `runsc` 필수, 네트워크 없음,
읽기 전용, 비루트, CPU 1개·메모리/스왑 1GiB·PID 64개·전체 통신/파싱/봉 실행 900초가 적용된다.
종료·시간 초과·프로토콜 오류는 컨테이너를 제거하며 부분 성과를 성공으로 반환하지 않는다.
900초는 신뢰된 제어부의 통계 후처리 시간까지 포함하는 보장은 아니다.

실제 실행·거대 중첩 반복·거대 할당 검증은 `test_pine_sandbox.py`, 세 언어 원장 일치는
`test_execution_parity.py`로 확인한다. 연구 VM endpoint를 해당 테스트 프로세스에만 지정한다.
