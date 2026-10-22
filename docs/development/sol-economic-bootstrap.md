# 봉인 후 경제 ARM bootstrap

계산 계약은 [Sol 전략 연구](./sol-strategy-lab.md)의 동결 경제 실행을 따른다. 새 경제 workflow는 기존 semantic workflow와 별개이며, 아직 실행하지 않았다. 실제 C8 품질 봉인·실제 종료 영수증으로 만든 경제 payload와 semantic execute overlay의 URL/SHA가 모두 들어오기 전에는 의존성 설치 전에 거절한다.

`sol-research-economics.yml`은 동일 소유자·공개 저장소·동일 저장소 PR925·첫 attempt·`sol-research-economics-execute` label만 받는다. 무료 표준 `ubuntu-24.04-arm` 16host에서 각 4process를 사용한다. 원 ordinal 1440과 사전 고정 shuffle 배치를 유지하고, 이미 소비한 job을 재시도하지 않는다. 실제 품질 봉인 전에 label을 붙이거나 실행하지 않는다.

bootstrap은 고정 base → freq1h revision → root의 semantic execute overlay → 경제 delta 순서로 인증한다. 기존 helper의 SHA를 먼저 확인하고 dependency/runtime/crypto/cleanup만 재사용한다. 경제 delta는 새 디렉터리의 source/inputs 사본에 25개 허용 파일만 추가한다. 기존 파일 덮어쓰기와 링크를 거절하며, base pending·manifest·입력 inventory·helper·3image를 대조한다. 원 semantic helper/workflow는 수정하지 않는다.

Release의 `epoch8-economic-remote-XX.claim.json`을 새로 예약한 뒤 worker를 시작한다. worker에는 복호화 키·GitHub token을 전달하지 않는다. 신규 세션의 실제 worker 종료를 수거하고, process group이 남으면 guest cleanup을 거절한다. 보호된 원 guest 이미지/runsc와 격리 정책은 기존 runtime 검사를 그대로 사용한다.

결과는 모든 원 cache·receipt·비공개 로그를 gzip한 뒤 `result-v8-economic-N` 문맥으로 AES-GCM 암호화한다. `epoch8-economic-N-RUNID.enc`만 게시하며 압축본·암호문 각각 2GiB Release 한도를 넘으면 파일을 삭제하거나 요약하지 않고 중단한다. 현재 원 run_job cache는 binding·metrics·count·해시를 저장하고 equity/minute 배열 본문은 저장하지 않는다. 실제 payload 크기는 미관측이므로 분할 필요 여부는 확인 전이다.

별도 root 수신기는 내려받은 asset metadata/암호문 SHA·size·run/shard를 대조하고 EOF/MAC 성공을 수거한 뒤에만 gzip tar를 읽는다. 성공한 worker·4lane·guest0·claim/plan/source binding만 새 비공개 host inbox에 단일 writer로 게시한다. 모든 cache와 비공개 wrapper/log는 `_bootstrap/`에 보존한다. 실패 pack은 진단 경로에 남고 계산 결과로 승격되지 않는다. 수신기는 경제 journal/report writer가 아니며 최종1440·family720+720·입력 해시 검증은 별도 원 root finalizer의 권한이다.

현재 검증 범위는 키 없는 환경·빈 CWD의 합성 unittest와 정적 검사다. 실제 품질/선정/CSV/수익률·원격 실행은 읽거나 실행하지 않았다. 실행 승인·URL/SHA 확정·공개 runner의 실제 성공은 별도 확인이 필요하다.
