# prompts — versioned agent system prompts

Per 05 DoD #3 and E8-3, prompts are the source of truth in git — never only inside n8n node fields.

Sync mechanism: n8n workflows load prompts at runtime via a Code Node that reads `/prompts/*.md` (mounted read-only in docker-compose). If `prompt-sync` is not yet wired, the manual sync is: copy file content into the AI Agent node's System Message field and export.

Files:
- `orchestrator_system.md` — WF-1 Level-1 planner/decomposer + tool policy (always Search_Tool_Store before Invoke_Lab)
- `lab_synthesis_system.md` — WF-2 Code Synthesis Agent
- `lab_explorer_system.md` — WF-2 API Explorer Agent
- `audit_security_system.md` — WF-3 Security Agent
- `audit_critic_system.md` — WF-3 Edge-Case Critic
- `mutation_rewrite_system.md` — WF-7 failure → mutation constraint rewriter (small fast model)
