# Release Sherpa

Powered by the Release Shepherd collector and review adapters.

An experimental, on-demand release-review tool for work completed by Paperclip agents.
It collects branch evidence, integrates eligible changes in isolated local Git worktrees,
and validates a reviewer’s readiness assessment against independent checks.

It does not push branches, merge into the target branch, deploy, or mark work shipped.
Installing the source does not start a listener or schedule release runs.

## Requirements

- Python 3.11+ and Git on macOS or Linux; SSH access to the Paperclip host.
- GitHub access already configured on that host. SSH host keys must be trusted explicitly.
- Repository-specific checks and independently obtained deployment evidence.
- Optional: VS Code with GitHub Copilot, or an authenticated Codex CLI for explicitly enabled quota fallback.

The core uses Python’s standard library. The optional Slack broker additionally needs
`python-dotenv`; see `slack-bridge/requirements.txt`. The sample Python test wrapper uses
macOS `sandbox-exec` and must be replaced with an appropriate sandbox on other systems.

## Configure and run

```sh
cp config.example.json config.json
# Edit config.json with your own host, company ID, repositories and checks.
python3 shepherd.py scan
python3 shepherd.py prepare --group example-app
python3 shepherd.py cycle --group example-app
```

`scan` records inventory. `prepare` creates a local integration worktree and runs configured
checks. `cycle` additionally hands off eligible reviews and validates returned results.
`check` refreshes source evidence and validates existing results. `scan --cached` supports
offline inspection; cached evidence cannot approve a release.

The example is deliberately unconfigured: it uses a reserved example hostname, has no
checks and disables automatic preparation. Supply commands as argument arrays, not shell
strings. For the macOS Python wrapper, set `SHEPHERD_TEST_PYTHON` to an existing test
environment and configure its command using the wrapper’s absolute path. The wrapper’s
sample environment is intended for Flask-style tests and must be adapted to your app.

Group `task_prefix` controls identifiers in branch names and Paperclip tasks (default
`APP`, for example `work/app12-fix` and `APP-12`). Sources describe repository names and
existing checkout paths on the SSH host. An optional `local_seed` can reuse local Git
objects. Every integration target must appear among the configured sources.

`config.json`, `bridge.local.json`, `.env` files and `state/` are ignored by Git.
Keep credentials in your existing SSH/Git credential stores or server-local environment;
never place tokens in tracked examples. The public repository contains no application
checkout, task inventory, customer data or deployment observations.

## Selection and readiness

Branches need an exact reference in task text, a recognized task identifier, and completed
associated tasks. Active, ambiguous or unassociated work remains held. Git ancestry and
patch-equivalence checks avoid reapplying changes already present in target history;
they do not prove that later changes preserve the original behavior. Squashed or
ambiguous history may need manual reconciliation.

Conflicted merges are aborted and recorded. A partial integration cannot be approved.
The tool creates dedicated Git cache refs on the remote host when fetching missing objects,
but does not change its checked-out source branches. Review worktrees remain local.

Approval requires matching run and commit IDs, successful independent checks, complete
integration, a clean unchanged checkout, unchanged branch and task evidence, and a fresh
stable deployment observation. A later evidence change revokes readiness. A launch,
queued request, missing result or model self-description is not readiness approval.

## Deployment evidence

The current deployment gate expects Render-style observations. A trusted operator or
separate read-only integration must refresh `state/deployments.json`; the standalone
runner does not fetch Render metadata itself. The format is:

```json
{
  "example-app": {
    "observed_at": "UTC_ISO_TIMESTAMP_FROM_YOUR_OBSERVATION",
    "service_id": "YOUR_RENDER_SERVICE_ID",
    "repo": "example-org/example-app",
    "branch": "main",
    "live_sha": "FULL_40_CHARACTER_COMMIT_SHA",
    "in_progress": false
  }
}
```

Observations expire after one hour and must match the configured repository, branch and
service. Missing or stale evidence blocks approval. Do not create observations from an
agent’s claim that a deployment succeeded.

## Review adapters

The optional [Copilot companion](copilot-bridge/README.md) uses the VS Code language-model
API with the `copilot` vendor. It is an experimental extension source, not a published
Marketplace package. The collector queues reviews only after a verified direct connection.

Codex fallback is disabled by default. Enable `review_policy.codex_on_quota_exhaustion`
only when you want it. Confirm quota exhaustion in local `state/copilot-status.json` with
`available: false` and `reason_code: "quota_exhausted"`. Other connection errors do not
implicitly enable fallback. Runs are marked `awaiting_codex`; an operator or the optional
Slack worker must perform the review. The collector CLI alone does not run Codex.

Legacy result filenames are `copilot-result.json` and `copilot-review.md` for either
reviewer. The assigned and recorded reviewer must match. Result files and receipts are
local conventions, not protection from other programs running as the same OS user.

## Optional Slack bridge

See [Slack setup](slack-bridge/README.md). The bridge accepts an exact request from a
configured owner, queues it over an existing SSH connection, and posts the outcome to the
originating Slack thread. The worker checks only for explicit requests; it does not
schedule release scans. No bot profiles, tokens or service installers are bundled.

## Development

```sh
python3 -m unittest discover -s . -q
python3 -m unittest discover -s slack-bridge -q
python3 -m unittest discover -s tools -q
node --test copilot-bridge/core.test.js
python3 tools/check_public_tree.py
```

Tests use temporary repositories and synthetic identities; they do not call live AI
models, Slack or deployment APIs. GitHub Actions runs the same deterministic checks.
Live integration testing requires your own configured environment. See
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE). Product names identify optional integrations; this project is not an
official Paperclip, GitHub, OpenAI, Slack or Render product.
