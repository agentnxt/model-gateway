# Pending Tasks for Code Deploy Agent

## 1. Containerization & Deployment
- [ ] Create a `Dockerfile` to containerize the agent for production.
- [ ] Add the agent service to the main `docker-compose.yml` (or create a dedicated compose file).
- [ ] Set up a CI/CD pipeline to automate the agent's deployment.

## 2. Security & Policy Integration
- [ ] **Policy Engine:** Replace the current LLM-based mock `policy_checker` with actual API calls to OPA (Open Policy Agent) and OpenFGA to enforce enterprise rules.
- [ ] **Secret Management:** Fully wire up `InfisicalAuthManager` so the agent fetches credentials (like `LANGFLOW_API_KEY`) dynamically at runtime rather than falling back to `.env` or dummy keys.

## 3. Skill & Handler Expansion
- [ ] **IAM/IGA Tasks:** Implement and wire up handlers for Identity and Access Management (e.g., Microsoft Entra ID, Keycloak, OpenFGA).
- [ ] **CMS Tasks:** Implement handlers for Content Management Systems (e.g., WordPress, Ghost, Liferay).
- [ ] **FinOps Tasks:** Implement cloud cost and billing skills (e.g., Lago, Google Cloud Billing).
- [ ] **Executor Routing:** Uncomment and integrate `handle_iam_task` and `handle_cms_task` in the `executor` node in `src/agent.py`.

## 4. Testing & Validation
- [ ] Add unit tests for the LangGraph nodes (`planner`, `reviewer`, `policy_checker`, `human_approval`, `executor`).
- [ ] Perform integration testing for the n8n and Langflow webhook triggers against live endpoints.
- [ ] Verify that all steps are correctly logging end-to-end traces in Langfuse.
