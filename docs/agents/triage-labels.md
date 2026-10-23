# Triage 분류

| 역할 | 분류값 | 의미 |
| --- | --- | --- |
| needs-triage | needs-triage | 검토 필요 |
| needs-info | needs-info | 추가 정보 필요 |
| ready-for-agent | ready-for-agent | 에이전트 구현 가능 |
| ready-for-human | ready-for-human | 사람의 구현 필요 |
| wontfix | wontfix | 진행하지 않음 |

분류가 필요한 백로그 항목에 `**Triage:** <분류값>`으로 기록한다.
기존 ACTIVE·PARTIAL·DEFERRED 판정을 대체하지 않는다.
wontfix의 종결 처리는 기존 백로그 규칙을 따른다.
GitHub 라벨은 생성하지 않는다.
