# Wimbly

Wimbly is a Growth engine for legal and financial services. This repository
contains its plugin for agents.

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

After installing, run `/wimbly:onboarding` in Claude Code or `$onboarding` in
Codex. Sign in to your Wimbly account when prompted.

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
