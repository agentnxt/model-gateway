# Cognitive Guard Schemas

## Canonical Redpanda Topic Schema
- `schemas/guardrails/redpanda/cognitive-drift-event/v1.json`

Topic:
- `cognitive-drift-events`

Schema Registry:
- Subject: `cognitive-drift-events-value`
- Compatibility: `backward`

## Protobuf Contract
- `schemas/guardrails/cognitive_guard.proto`

Services covered:
- intent-registry
- CoT auditor
- constraint-injector
- drift-scorer
- memory-isolator
- sycophancy-guard
