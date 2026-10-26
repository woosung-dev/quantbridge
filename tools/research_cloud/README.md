# 기간 연구 ARM64 pilot

로컬 연구와 같은 고정 코드·데이터·ARM64 이미지로 세 원본의 1h/P1 A/B 여섯 결과를 재계산한다. Pine/shared, Python/shared, Python/position_feedback를 각각 한 VM에서 실행한다. 기존 계산은 계속 동작한다.

`research-arm64-pilot-v1` label과 고정 소유자·브랜치 조건을 만족한 스택 PR에서만 public 표준 `ubuntu-24.04-arm`이 실행된다. 최대 두 VM을 병렬 사용한다. 입력은 파일 목록·SHA를 고정한 암호문이고, 원래 결과 바이트를 포함하지 않는다. 과거 요청·결과 SHA 여섯 쌍을 비교 기준으로 사용한다.

`package.py`는 검토한 입력을 봉인하고 `bootstrap.py`는 일회용 VM의 정확한 runsc/sidecar/image를 설치한다. `runner.py`는 원래 `run_group`을 호출한다. 전략 원문·생성 코드는 gVisor 안에서 실행하며 호스트는 실행하지 않는다. 실제 Docker 생성·격리 설정·종료와 A/B 두 결과의 바이트 일치를 함께 검사한다.

키와 GitHub 토큰은 전송·암복호화 단계에만 제공한다. 데이터 계산 중 앱 설정 import가 요구하는 거래 암호화 키는 실행마다 만든 일회용 값으로 충족한다. 원본·환경 파일·토큰을 로그에 출력하지 않는다. 암호화된 입력과 최대8MiB 결과는 미게시 draft release asset으로 보관한다. Actions artifact/cache 저장은 사용하지 않는다. [표준 public runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)와 [release 파일 한도](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)를 따른다.

검증 명령: `python3 -m unittest discover -s tools/research_cloud/tests -v`. 파일 경로/링크/중복/해시·빈 결과·환경키·격리 설정 반례를 검증한다. 테스트는 실제 Docker나 전략을 실행하지 않는다.

이 pilot은 다른 기간의 병렬 적격성이나 공식 결과 가져오기를 자동 승인하지 않는다. 공통 A/B·비용·체결·준비봉1000·동결 구현은 유지하며, 검증 완료 후 정확한 범위와 원본 소유권을 별도로 배정한다.
