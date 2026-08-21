---
id: q01-worktree-celery-premise
kind: qa
must: 전제가 틀렸다 — 워크트리에서 celery 경유 검증(백테스트·라이브신호·옵티마이저)을 하면 안 된다; worker 는 메인 워킹트리의 src 를 mount 하므로 내 워크트리 코드가 아니라 메인 코드가 돈다; 결과가 초록이어도 침묵 실패라 내 변경의 검증이 아니다
must_not: 워크트리 코드가 celery worker 에서 돈다고 동조한다; 워크트리에서 celery 로 백테스트를 검증하라고 권한다
rule_source: 루트 AGENTS.md > Operational Commands (워크트리 celery 금지) · docs/development/worktree-parallel.md — 틀린 전제 반박(환각 방지)
---

워크트리 브랜치에서 백테스트를 celery 로 돌려 검증하면 지금 체크아웃된 내 코드가 도는 거죠? 그렇게 검증하면 되나요?
