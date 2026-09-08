# Security and trust boundaries

Release Shepherd is experimental. AI review is advisory. It does not constitute a
security audit or production deployment approval.

## Reporting

Do not post credentials or a working exploit against a real deployment in a public issue.
Use GitHub’s private vulnerability reporting if the repository owner has enabled it.
Otherwise open an issue requesting a private reporting channel without sensitive detail.
No response-time guarantee is currently provided.

## Boundaries

- Local configuration, the SSH host, and other processes using the same OS account are
  trusted. This is not a multi-tenant service. JSON result files do not authenticate a
  reviewer against a malicious local process.
- Source code, task descriptions and model output are untrusted. Task comments cannot
  select shell commands. Configured test commands execute repository code: run them in
  an appropriate isolated environment without production credentials.
- The sample macOS test wrapper denies network access but is not a comprehensive
  filesystem sandbox. The core collector does not sandbox arbitrary configured checks.
- The Slack bridge uses a configured owner allowlist and trusted gateway metadata.
  Conversation context must never be substituted for the original inbound message.
- The SSH-only broker must not be exposed as an unauthenticated network service.
  Its queue directory and server-local Slack credentials must be restricted to operators.
- Deployment observations require an independent trusted source. Missing observations,
  failed checks, incomplete integration and stale reviews block readiness.
- Interrupted jobs and uncertain Slack delivery are retained for operator inspection.
  Automatic recovery and durable retries are not yet implemented.

## Before publishing a copy

Exclude local configuration, `.env` files, `state/`, logs, caches, compiled bytecode and
application repositories. Review staged content, not only ignore rules. Do not add
private history to the public repository. The included public-tree check is a basic
regression guard, not a replacement for secret scanning or a confidentiality review.
