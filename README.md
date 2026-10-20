# Wimbly

Set up Wimbly from Claude or Codex. Connect your account and follow the
remaining onboarding steps.

**Preview.** Requires an enrolled Wimbly account. The setup service is awaiting
deployment and live sign-in testing. Marketplace listings are pending.

## Install

In Claude Code:

```text
/plugin marketplace add wimbly-ai/agent-plugins
/plugin install wimbly@wimbly
```

In Codex:

```sh
codex plugin marketplace add wimbly-ai/agent-plugins
codex plugin add wimbly@wimbly
```

Connect `wimbly-setup` when prompted. Run `/wimbly:onboarding` in Claude Code
or `$onboarding` in Codex. You can also ask, “Help me set up Wimbly.”

The assistant checks progress and links to Wimbly's website to connect your
mailbox and LinkedIn, review your background, and confirm your ideal clients.
After each step, return to the conversation to continue. This plugin reads
setup progress only. Research and outreach happen in Wimbly's mail panel.

[Support and account access](https://www.wimbly.ai/contact) ·
[Privacy](https://www.wimbly.ai/legal-pages/privacy-policy) ·
[Terms](https://www.wimbly.ai/legal-pages/terms-conditions)

## Maintain

Python 3.12 or later; no dependencies.

```sh
python3 scripts/validate.py
python3 scripts/package.py
```

The ZIP is written to `dist/` and includes only the plugin files. To release,
update both manifest versions and push a matching `v<version>` tag. CI validates
the package and attaches the ZIP to a GitHub prerelease.

Installation follows `main`; released ZIPs are available under
[Releases](https://github.com/wimbly-ai/agent-plugins/releases). To update, run
`claude plugin update wimbly@wimbly` or
`codex plugin marketplace upgrade wimbly`, then restart the client.
