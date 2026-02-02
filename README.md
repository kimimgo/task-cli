# task-cli

CLI 기반 할일 관리 도구 - DevSwarm 병렬 구현 검증용 프로젝트

## DevSwarm Status

이 프로젝트는 DevSwarm Phase 0이 완료되었습니다.

### 구현 태스크

| ID | Name | Dependencies | Status |
|----|------|--------------|--------|
| IMPL-001 | Core Models | DESIGN-001 | Pending |
| IMPL-002 | Storage Layer | IMPL-001 | Pending |
| IMPL-003 | CLI Commands | IMPL-002 | Pending |
| IMPL-004 | Integration Tests | IMPL-003 | Pending |

## 실행 방법

```bash
# DevSwarm 오케스트레이터 실행
cd /home/imgyu/workspace/cc-kimimgo/plugins/cc-swarm-orchestrator
python3 -c "
from core import ContainerOrchestrator, TaskSource

source = TaskSource(
    graph_path='/home/imgyu/workspace/task-cli/specs/dependency/graph.yaml',
    sync_with_github=False
)
orchestrator = ContainerOrchestrator(
    task_source=source,
    workspace='/home/imgyu/workspace/task-cli'
)
results = orchestrator.run(dry_run=True)
print(results)
"
```

## Usage (구현 후)

```bash
# 태스크 추가
task add "우유 사기" --priority high

# 태스크 목록
task list

# 태스크 완료
task done 1

# 태스크 삭제
task delete 1
```
