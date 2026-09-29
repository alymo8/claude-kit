# Phase D: security and safety

Audit security and safety against the production bar. Do not write exploit
code: describe the vulnerability, the affected path and the fix.

Cover:

- **Authentication:** mechanism, token handling, expiry, refresh, session
  management.
- **Authorization:** enumerate every externally reachable route, endpoint,
  handler or tool. For each, state what authorization check it performs and
  cite the line. Present this as a table, then write findings for every entry
  with no check.
- **Tenant and user isolation:** can one tenant's identifier reach another
  tenant's data? Trace at least two data-access paths end to end.
- **Input validation:** unvalidated input reaching queries, filesystem paths,
  shell commands, deserializers or template renderers.
- **Injection surfaces:** SQL, command, path traversal, SSRF and prompt
  injection. For prompt injection, identify every point where untrusted
  content (user input, retrieved documents, tool results, web content, file
  uploads) enters a model's context and what, if anything, separates it from
  instructions. Assess what an injected instruction could actually cause,
  given the tools the model can call.
- **Tool permissions:** what can an agent do without human approval, and what
  is the blast radius of the most dangerous tool it can call unattended?
- **Local developer-agent config:** `.claude/settings.json`,
  `.claude/settings.local.json`, `.mcp.json` and hooks, using the security
  items of section 4 of the rules. Flag hooks that run commands automatically
  on tool use, broad permission grants or allowlists, auto-approve settings,
  and MCP servers with wide scope or untrusted sources. Note whether local
  override files are gitignored.
- **Secrets:** hardcoded credentials in source or git history, secrets in logs
  or error messages, secrets in model context. Never copy a secret's value
  into the report.
- **Data handling:** what PII or sensitive data flows through, where it is
  stored, what is logged, retention, and what is sent to third parties.
- **Dependency CVEs**, if checkable offline.
- **Output handling:** is model output rendered as HTML, executed, passed to a
  shell, or written to disk without sanitization?

End with `## What is missing` and `## Top 10`, ranked by severity then effort.
