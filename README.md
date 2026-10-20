# Wimbly

Wimbly is an AI business-development analyst for partners at professional-services
firms. This repository contains its plugin for Claude and Codex.

## Install

**Preview.** Account connection is awaiting deployment and live sign-in testing.
An enrolled Wimbly account is required. Marketplace listings are pending.

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

When prompted, sign in to your Wimbly account.

## Skills

| Skill | Claude Code | Codex |
| --- | --- | --- |
| [Onboarding](skills/onboarding/SKILL.md) | `/wimbly:onboarding` | `$onboarding` |

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
