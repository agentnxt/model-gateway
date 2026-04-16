# Model Token Limits Reference

Use these values for `max_tokens` guidance and context window planning.

## Local Models
| Model Alias | Context Window | Max Output |
|---|---|---|
| ollama/llama3 | 8,192 | 4,096 |
| ollama/mistral | 32,768 | 4,096 |
| vllm/llama3-70b | 8,192 | 4,096 |
| tgi/mistral-7b | 32,768 | 4,096 |

## OpenAI
| Model | Context Window | Max Output |
|---|---|---|
| gpt-4o | 128,000 | 16,384 |
| gpt-4o-mini | 128,000 | 16,384 |
| o1-preview | 128,000 | 32,768 |

## Anthropic / Claude
| Model | Context Window | Max Output |
|---|---|---|
| claude-sonnet-4-5 | 200,000 | 8,192 |
| claude-haiku-4-5 | 200,000 | 8,192 |

## Google Gemini
| Model | Context Window | Max Output |
|---|---|---|
| gemini-1.5-pro | 2,000,000 | 8,192 |
| gemini-1.5-flash | 1,000,000 | 8,192 |

## Microsoft Azure OpenAI
Same as OpenAI model limits above — depends on the deployed model.

## AWS Bedrock
| Model | Context Window | Max Output |
|---|---|---|
| claude-3-sonnet (bedrock) | 200,000 | 4,096 |
| llama3-70b (bedrock) | 8,192 | 2,048 |

## Mistral AI
| Model | Context Window | Max Output |
|---|---|---|
| mistral-large-latest | 128,000 | 4,096 |
| mistral-small-latest | 128,000 | 4,096 |

## Groq
| Model | Context Window | Max Output |
|---|---|---|
| llama3-70b-8192 | 8,192 | 8,192 |
| mixtral-8x7b-32768 | 32,768 | 32,768 |

## Fireworks AI
| Model | Context Window | Max Output |
|---|---|---|
| llama-v3-70b-instruct | 8,192 | 4,096 |

## Together AI
| Model | Context Window | Max Output |
|---|---|---|
| llama-3-70b-instruct | 8,192 | 4,096 |

## OpenRouter
| Model | Context Window | Max Output |
|---|---|---|
| auto | Varies by routed model | Varies |
| anthropic/claude-3-opus | 200,000 | 4,096 |

## Notes
- LiteLLM enforces `max_tokens` at the proxy level — set it in router_settings or per-model
- For cost accuracy, LiteLLM uses these limits to calculate input vs output token costs
- `drop_params: true` in litellm_settings prevents errors when a model doesn't support a param
