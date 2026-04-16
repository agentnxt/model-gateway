# Autonomyx LLM Gateway — Default Values

Use these when user says "generate defaults" or does not supply values.

## Network
| Setting | Default |
|---|---|
| Gateway port | 4000 |
| Ollama host | host.docker.internal:11434 |
| vLLM host | host.docker.internal:8000 |
| TGI host | host.docker.internal:8080 |
| Coolify VPS | vps.agnxxt.com |

## Credentials
| Setting | Default |
|---|---|
| LITELLM_MASTER_KEY | `sk-autonomyx-$(openssl rand -hex 8)` (generate fresh) |
| Postgres user | `litellm` |
| Postgres password | `litellm_pass` (remind user to change) |
| Postgres DB | `litellm` |
| DATABASE_URL | `postgresql://litellm:litellm_pass@litellm-db:5432/litellm` |

## Budget
| Setting | Default |
|---|---|
| max_budget | 10.00 (USD, per key) |
| budget_duration | 30d |
| soft_budget | 8.00 |

## Router
| Setting | Default |
|---|---|
| routing_strategy | usage-based-routing |
| num_retries | 3 |
| request_timeout | 60 |
| allowed_fails | 2 |

## Grafana
| Setting | Default |
|---|---|
| Admin user | admin |
| Admin password | autonomyx |
| Dashboard ID | 17587 (official LiteLLM community dashboard) |
