---
name: jina-ai-pythondocs
description: Fetch Python documentation in a clean, LLM-friendly format using Jina AI's web service.
---
## Skill: Fetching Python Documentation via Jina AI

**Trigger:** When you need to read online Python documentation, library references, or API guides to understand how to implement a function or class.
**Rationale:** Standard web scraping returns token-heavy HTML, and local terminal pagers block the execution loop. The `r.jina.ai` service instantly converts documentation URLs into clean, LLM-friendly Markdown.

**Execution Steps:**
1. Identify the exact URL of the documentation you need to read (e.g., `https://docs.python.org/3/library/subprocess.html`).
2. Execute the following command in `cmd.exe` using the built-in `curl` tool. Prefix the target URL with `https://r.jina.ai/`:
   ```cmd
   curl -s "[https://r.jina.ai/](https://r.jina.ai/)<TARGET_URL>"
   ```

**Critical Rules for Agent:**
- Always enclose the full Jina URL in double quotes (`"`) within the `curl` command to prevent `cmd.exe` from breaking on special characters like `&` or `?`.
- Strictly use `cmd.exe` syntax (`type`, `del`, `>`). Do not use PowerShell cmdlets.
- Do not execute `python -m pydoc` or `help()` under any circumstances, as it will hang the session.
