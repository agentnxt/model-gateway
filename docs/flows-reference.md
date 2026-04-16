# Flows Reference

12 pre-built workflows. Call any via the Langflow API with your API key.

**Base URL:** `https://flows.openautonomyx.com/api/v1/run/{flow_name}`
**Auth:** `Authorization: Bearer lf-your-api-key`

All flows return JSON.

---

## gateway-agent

General-purpose AI agent with automatic language detection, model routing, and feedback capture.

**Input:**
```json
{
  "input_value": "Your message or task"
}
```

**What it does:** Detects language → recommends model → runs LLM → captures feedback async

**Use when:** You want the gateway to handle everything automatically.

---

## code-review

Automated code review returning structured JSON.

**Input:**
```json
{
  "input_value": "paste your code here",
  "language": "python",
  "context": "production API endpoint"
}
```

**Output:**
```json
{
  "overall_score": 4,
  "summary": "...",
  "bugs": [{"severity": "critical", "line": 12, "description": "...", "fix": "..."}],
  "security": [...],
  "style": [...],
  "improvements": [...],
  "positive": [...]
}
```

**Model:** Qwen2.5-Coder-32B (always — consistent quality)

---

## policy-creator

Generate Privacy Policy, Terms of Service, and Cookie Policy documents.

**Input:**
```json
{
  "product_name": "InvoiceAI",
  "product_description": "B2B SaaS for invoice automation serving Indian SMEs",
  "policy_types": "privacy_policy,terms_of_service,cookie_policy",
  "jurisdictions": "India (DPDP 2023)",
  "sub_processors": "Razorpay, Supabase",
  "company_details": "InvoiceAI Pvt Ltd, Bengaluru, hello@invoiceai.com"
}
```

**Output:** Full markdown policy documents per type + compliance flags + missing information list

**Note:** AI-generated. Always review with qualified legal counsel before publishing.

---

## policy-review

Analyse any vendor policy document across 5 domains.

**Input:**
```json
{
  "vendor_name": "Razorpay",
  "policy_text": "<paste full policy text>",
  "review_context": "We handle financial data. Need DPDP 2023 compliance."
}
```

**Output:**
```json
{
  "risk_level": "medium",
  "domains": {
    "privacy_data_usage": {"score": 72, "findings": [...], "red_flags": [...]},
    "ai_ml_training": {"trains_on_user_data": false, "opt_out_available": true, ...},
    "security_posture": {"certifications": ["PCI-DSS", "ISO 27001"], ...},
    "carbon_sustainability": {...},
    "governance": {"gdpr_compliant": true, "dpdp_2023_compliant": "unclear", ...}
  },
  "deadline_actions": [...],
  "opt_out_instructions": {...}
}
```

---

## feature-gap-analyzer

Compare any two enterprise software products across 8 dimensions.

**Input:**
```json
{
  "product_a": "Salesforce",
  "product_b": "HubSpot",
  "category": "CRM",
  "focus_areas": "AI features, pricing, mobile"
}
```

**Output:** Scored matrix (0–100 per dimension), advantages, gaps, recommendation, confidence level.

---

## saas-evaluator

Multi-persona enterprise SaaS evaluation.

**Input:**
```json
{
  "product_name": "Linear",
  "persona": "CTO",
  "use_case": "Project management for 80-person engineering team",
  "org_size": "80-person startup"
}
```

**Output:** 8-dimension scores, strengths, weaknesses, alternatives, questions for vendor, next steps.

**Personas:** CTO, CISO, Procurement, IT Admin, Dept Head, Legal

---

## fraud-sentinel

Real-time transaction fraud detection.

**Input:**
```json
{
  "transaction_details": "₹1 transfer to new account at 3am via new device",
  "platform_context": "P2P payment app",
  "user_history": "3-year account, recent password reset"
}
```

**Output:**
```json
{
  "verdict": "STRONG_WARN",
  "risk_score": 84,
  "identity_risk": "HIGH",
  "patterns_detected": [
    {"pattern": "probe_transaction", "confidence": 91},
    {"pattern": "new_device_anomaly", "confidence": 78},
    {"pattern": "time_anomaly", "confidence": 65}
  ],
  "citizen_safety_note": "This looks like a test transaction from an unrecognised device at an unusual time. Proceed with caution.",
  "evidence_for_claim": "TXN-2026-xxxxx — usable for cybercrime.gov.in report"
}
```

**DPDP 2023 compliant. Zero PII stored.**

---

## app-alternatives-finder

Find OSS and commercial alternatives to any software.

**Input:**
```json
{
  "product_name": "Notion",
  "preference": "open-source only",
  "max_results": "10"
}
```

**Output:** Ranked list with feature overlap %, licence, self_hostable flag, pricing summary, sources.

---

## saas-standardizer

Exhaustive 18-dimension product profile.

**Input:**
```json
{
  "product_name": "Supabase",
  "dimensions": "all"
}
```

**Output:** Features, use cases, login methods, API details, integrations, pricing, security certs, support SLA, open source health, funding, analyst rankings, community sentiment, notable clients.

---

## oss-to-saas-analyzer

Score any OSS project across 5 commercial service archetypes.

**Input:**
```json
{
  "github_repo": "langfuse/langfuse",
  "target_market": "Indian SaaS companies",
  "context": "We already run a managed hosting business"
}
```

**Output:** Scores for managed hosting, API service, consulting, managed ops, and vertical SaaS. Recommended mix, 90-day action plan, risks.

---

## structured-data-parser

Parse structured data without an LLM — pure Python.

**Input:**
```json
{
  "raw_data": "[{\"name\": \"Alice\", \"score\": 95}, {\"name\": \"Bob\", \"score\": 87}]",
  "format": "json",
  "extract_fields": "name,score"
}
```

**Output:** Parsed JSON with record count. Supports JSON, CSV, XML, YAML, Markdown tables.

---

## web-scraper

Crawl any URL and index into SurrealDB for RAG.

**Input:**
```json
{
  "url": "https://docs.langfuse.com",
  "depth": "-1",
  "max_pages": "20",
  "collection_name": "langfuse_docs"
}
```

**depth:** `0` = single page, `-1` = full site, `N` = N levels deep

**Output:**
```json
{
  "status": "done",
  "pages_scraped": 18,
  "chunks_embedded": 1243,
  "collection": "langfuse_docs",
  "result_summary": {
    "rag_query_example": "SELECT * FROM langfuse_docs WHERE embedding <|5,40|> $query_embedding"
  }
}
```

**Pipeline:** Playwright (Chromium) → chunk → Qwen3-30B extract → nomic-embed-text → SurrealDB Cloud (MTREE vector index)
