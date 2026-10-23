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
Codex. Sign in to your Wimbly account when prompted. The same connection
provides Wimbly tools after onboarding.

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

For a local or workspace ChatGPT upload, set `OPENAI_APP_ID` to the actual
registered MCP server ID, then build its host-specific archive:

```sh
python3 scripts/package.py --openai-app-id "$OPENAI_APP_ID"
```

Use an `asdk_app_`, `connector_`, or `templated_apps_` ID. A UI route such as
`plugin_asdk_app_...` includes a `plugin_` prefix that is not part of the mapping
ID and is rejected. This writes `dist/wimbly-<version>-chatgpt.zip`; `--output`
overrides the destination. The generated `.app.json` binds the registered server.
ChatGPT expects one plugin manifest, so this archive places portable files at its
root and omits Claude compatibility files and marketplace catalogs. The default
build remains the universal archive for Claude and native clients.

The portable `mcp.json` declares OAuth with CIMD client registration for OpenAI
and the canonical Wimbly resource. Endpoints are discovered from the server;
credentials do not belong in the package. Keep this declaration when editing
connection metadata, following [OpenAI's authentication guidance](https://developers.openai.com/plugins/build/plugins#configure-mcp-authentication).

Installation follows `main`; released ZIPs are available under
[Releases](https://github.com/wimbly-ai/agent-plugins/releases). To update, run
`claude plugin update wimbly@wimbly` or
`codex plugin marketplace upgrade wimbly`, then restart the client.
