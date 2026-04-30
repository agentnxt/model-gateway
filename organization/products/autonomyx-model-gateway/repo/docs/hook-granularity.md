# Hook Granularity Contract

## Required phases
1. `pre_tool`
2. `post_tool`
3. `post_completion`

## Required execution order
1. Fire `pre_tool`
2. Call `behavioral-gate.Check`
3. If verdict=`BLOCK`, abort tool invocation
4. Else execute tool
5. Fire `post_tool` with output or error metadata
6. Fire `post_completion`
7. Call `cot-auditor.SubmitReasoning`

## Reliability semantics
- `pre_tool`: synchronous + blocking
- `post_tool`: async-capable but guaranteed delivery (retry + DLQ)
- `post_completion`: async-capable but guaranteed delivery (retry + DLQ)
- Post hooks must fire on success and failure paths

## Topic suggestions (Redpanda)
- `guardrails.hooks.pre-tool.v1`
- `guardrails.hooks.post-tool.v1`
- `guardrails.hooks.post-completion.v1`

## Keying
- Message key: `tenant_id:agent_id:task_id`
