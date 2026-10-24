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
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

The default ZIP is written to `dist/` and includes only the plugin files. Build
both directory archives and their checksums with:

```sh
python3 scripts/prepare_release.py
```

This writes `wimbly-<version>.zip` for Claude/native clients,
`wimbly-<version>-openai-submission.zip` for OpenAI's public portal,
`SHA256SUMS`, and `release.json`. The OpenAI archive has one manifest at its root,
declares the canonical OAuth MCP server, and contains no registered-app mapping.
`release.json` records the source commit and the remaining provider actions; it
does not report a submission or publication as completed.

### Release to the directories

1. Update both manifest versions, commit, merge to `main`, and push a matching
   `v<version>` tag. The tagged commit must include these release workflows.
   CI validates the source and attaches both archives, checksums and the release
   manifest to a GitHub **prerelease**. A tag or prerelease leaves the directory
   branch unchanged.
2. When that candidate is ready, mark its GitHub release as a full release. The
   `Release to plugin directories` workflow tests again, checks public production
   MCP discovery, and verifies existing release assets byte for byte. Missing
   assets are uploaded; published files are never overwritten. Prepare the
   prerelease assets before making a release immutable.
3. Only after those checks pass does the workflow advance `directory-release`
   to the exact release commit. It requires the tag, event SHA, both manifest
   versions and archive checksums to agree. The commit must belong to `main`;
   promotion is a normal fast-forward push and refuses version reductions,
   history rewrites and old release events. Retries of the same release are safe.
4. Claude checks that branch through its configured webhook or scheduled poll.
   OpenAI's package upload remains an explicit portal action, using the attached
   `-openai-submission.zip`. Complete the applicable review and publication there.

The public preflight uses no credentials and makes no authenticated tool calls.
Its timestamped `preflight.json` is a workflow artifact, separate from immutable
release files. Promotion requires a check for the same commit within 15 minutes.
It verifies production resource/issuer metadata, authentication challenges, PKCE,
CIMD, and private-route fences; actual OAuth, tools and UI need host testing.
This repository releases plugin packages and Claude's source reference. The
Wimbly backend continues to use its own deployment workflow.

### One-time directory setup

- **Claude:** submit this repository's root plugin and its canonical MCP server
  from the Wimbly organization. Once the first full GitHub release creates
  `directory-release`, set the plugin's **Tracked branch or tag** to that branch.
  Enable the portal's GitHub push updates and **Publish new versions
  automatically** where available. Anthropic controls the review setting:
  the first version, or every version, may still need a reviewer. Until a newer
  version is published, the existing published version remains live. See
  [Claude's update and publication rules](https://claude.com/docs/plugins/submit).
- **OpenAI:** use **With MCP** with `https://mcp.wimbly.ai/mcp`, the public
  submission ZIP, and the verified Wimbly publisher identity. Enter reviewer
  access only in the portal. After initial publication, eligible hosted MCP
  changes are scanned automatically, or can be rescanned in the portal. Skills,
  icons and listing changes require a new package upload and review. This
  workflow prepares those files and does not automate the portal's attestations
  or claim review approval. Keep the MCP URL stable. See
  [OpenAI's submission and update rules](https://developers.openai.com/plugins/deploy/submission).

Both portals need their initial submission/review setup before automatic
updates can operate. Branch protection or token permissions that block
`directory-release` cause the workflow to fail; it does not override them.

### Local or workspace ChatGPT installs

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
The mapped `-chatgpt.zip` is for private tests and workspace installations;
use `-openai-submission.zip` for the public directory instead.

The portable `mcp.json` declares OAuth with CIMD client registration for OpenAI
and the canonical Wimbly resource. Endpoints are discovered from the server;
credentials do not belong in the package. Keep this declaration when editing
connection metadata, following [OpenAI's authentication guidance](https://developers.openai.com/plugins/build/plugins#configure-mcp-authentication).

Installation follows `main`; released ZIPs are available under
[Releases](https://github.com/wimbly-ai/agent-plugins/releases). To update, run
`claude plugin update wimbly@wimbly` or
`codex plugin marketplace upgrade wimbly`, then restart the client.
