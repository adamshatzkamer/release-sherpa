# Copilot companion (experimental)

This folder contains an unpackaged VS Code extension. Open it as an extension development
workspace and launch it using your standard VS Code extension development workflow.
Set `SHEPHERD_STATE_ROOT` in the extension host environment to the collector’s absolute
`state` directory; for a development checkout it defaults to the sibling `state/` folder.

Run **Release Shepherd: Connect Copilot Reviewer** and complete any Copilot authentication
or consent prompts. A successful direct provider check writes local connection status.
The collector then queues eligible jobs for this extension. It uses only models registered
with vendor `copilot`, never the generic chat command. Source files are read from the
reviewed commit; the extension does not run arbitrary model-provided shell commands.

The extension writes the result, detailed report and a local provider receipt. These files
are not cryptographic proof against other processes running as your OS user. The collector
still applies independent readiness gates. Never infer approval from connection success.

No Marketplace publication, signed package or live integration compatibility guarantee is
included. Run `node --test core.test.js` for deterministic parser/provider/path tests.
The implementation uses the [VS Code Language Model API](https://code.visualstudio.com/api/extension-guides/ai/language-model).
