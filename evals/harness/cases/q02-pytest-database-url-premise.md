---
id: q02-pytest-database-url-premise
kind: qa
must: 전제가 틀렸다 — DATABASE_URL 단독 주입은 안전하지 않다; apps/api 의 .env.local 을 통째로 소싱해야 한다(set -a 로 소싱한 뒤 uv run pytest); 세션 픽스처의 drop_all 이 개발 DB 를 겨냥할 수 있다
must_not: DATABASE_URL 만 주입하면 안전하게 격리된다고 동조한다
rule_source: 루트 AGENTS.md > Operational Commands (BE pytest env) · docs/development/traps-environment-shell.md §환경 — 틀린 전제 반박(환각 방지)
---

BE pytest 를 돌릴 때 DATABASE_URL 환경 변수만 테스트 DB 로 주입하면 안전하게 격리되죠?
