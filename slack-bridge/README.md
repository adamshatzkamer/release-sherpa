# Optional Slack request bridge (experimental)

This adapter targets a Hermes-compatible `agent:start` hook. It is not a Slack app
installer. You must already operate a bot with authenticated event handling and permission
to post replies. Installation and service restarts are manual.

1. Copy `bridge.example.json` to ignored `bridge.local.json` on the worker and server.
   Configure the owner ID, group, queue path, bot/profile mapping and SSH broker location.
   `SHEPHERD_BRIDGE_CONFIG` can point to another local file. Multiple bots use distinct
   `bot_id` values and the same queue and profile mapping; both sides must agree.
2. Install `requirements.txt` in the server’s broker environment. Each configured profile
   has its own private `.env` containing `SLACK_BOT_TOKEN`; do not copy tokens to the Mac.
3. Put `handler.py`, `settings.py` and `HOOK.yaml` together in the gateway’s hook directory.
   Provide `SHEPHERD_BRIDGE_CONFIG` to that process. The hook requires these trusted fields:
   `platform`, `user_id`, `chat_id`, `thread_id`, `message_id`, and `raw_message`.
   The last two must come directly from the original platform event. Some gateway
   versions expose only enriched/truncated conversation text; those versions require an
   adapter change before this hook will work. The hook fails closed without raw text.
4. Place `broker.py` and `settings.py` on the SSH host at the configured path. Ensure the
   SSH account can read its local bridge config and private bot environment. Restrict the
   queue to that account. Validate the gateway in a test conversation before use.
5. Run `python3 slack-bridge/worker.py --once` to check the queue once, or omit `--once`
   to keep listening. You can run it under your own service supervisor. No service
   definition or automatic installer is included.

Accepted owner messages: `Run release review`, `Run release shepherd`, or
`Run release shepherd now`, optionally mentioning the bot. Other text, quoted commands,
and other users do not trigger it. The hook deduplicates by bot, channel and message ID.
The broker posts a pickup confirmation; the bot should not claim a request was queued
solely because it recognized the phrase.

The worker runs configured collection/checks and processes explicitly assigned Codex
fallback reviews. It does not refresh deployment metadata. Copilot jobs can be queued,
but this worker currently does not remain attached to await their later completion;
run the collector’s `check` command after the Copilot review. For unattended use, add an
explicit completion handler before relying on Copilot result notifications.

A sleeping/offline worker leaves requests queued. Jobs interrupted after pickup remain
`running`; failed or uncertain result delivery may remain `delivery_pending`. Inspect the
queue and local `state/slack-last-result.json` before retrying, to avoid duplicate work or
messages. This version is designed for a single trusted worker, not automatic failover.
