# Maintaining the Wimbly plugin

## Local checks and builds

Python 3.12 or later; no dependencies.

```sh
python3 scripts/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/preview_release.py --check-live
open dist/review.html
```

`prepare_release.py` builds both archives without the review page. `package.py`
builds only the universal archive. Files are selected by the explicit allowlist
in [scripts/validate.py](scripts/validate.py).

| Output | Use |
| --- | --- |
| `wimbly-<version>.zip` | Claude/native clients; plugin folder at archive root |
| `wimbly-<version>-openai-submission.zip` | Public OpenAI upload; one root manifest, no private app mapping |
| `SHA256SUMS`, `release.json` | Archive hashes, source commit and provider handoff |
| `review.html`, `review.json` | Package review; not a screenshot or provider approval |
| `preflight.json` | Timestamped public discovery checks when `--check-live` is used |

Review files are outside the submission archives. PR validation puts the review
page and packages in its **wimbly-plugin** artifact. The manual preview workflow
uses **wimbly-release-preview** and needs no Wimbly credentials.

## Inspect live tools

Tools come from `https://mcp.wimbly.ai/mcp`, not the plugin ZIP. The offered set
can vary with the signed-in account's enabled capabilities. The onboarding
review cases call `get_setup_status`; that is not a complete inventory.

Use the existing publisher draft's **MCPs → Wimbly** page, a private host
installation, or [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

```sh
npx @modelcontextprotocol/inspector --server-url https://mcp.wimbly.ai/mcp --transport http
```

Sign in, then select **Tools → List Tools** to review names, display titles,
descriptions, schemas and annotation hints. Listing metadata does not invoke
a tool. To include it in the local review page, save only the complete
`tools/list` JSON response, then run:

```sh
python3 scripts/preview_release.py --tools-json /tmp/wimbly-tools.json
```

Capture every page when `nextCursor` is present. The importer selects tool
definitions and excludes unrelated capture fields; it does not independently
verify the snapshot's origin or freshness. Never use an auth/session export
or commit credentials. [OpenAI testing and metadata refresh](https://developers.openai.com/plugins/deploy/connect-chatgpt).

## Private ChatGPT install

Register the test MCP server in ChatGPT, then use its actual ID:

```sh
python3 scripts/package.py --openai-app-id "$OPENAI_APP_ID"
```

Accepted prefixes: `asdk_app_`, `connector_`, `templated_apps_`. Remove the
`plugin_` UI route prefix. This produces `dist/wimbly-<version>-chatgpt.zip`
with `.app.json`, one root manifest and no Claude catalogs. `--output` changes
the destination. This mapped ZIP is for private/workspace installs; public
submission uses the separate `-openai-submission.zip`.

Keep the canonical OAuth/CIMD declaration in [mcp.json](mcp.json). Credentials
belong in the provider portal, never in the package.
[OpenAI authentication reference](https://developers.openai.com/plugins/build/plugins#configure-mcp-authentication).

## One-time directory setup

- **Claude:** submit this repository's root plugin and the MCP server from the
  Wimbly organization at [the developer portal](https://claude.ai/directory/manage).
  The first manual delivery creates `directory-release`; set **Tracked branch
  or tag** to that branch and configure push updates and auto-publish as allowed.
  A listing tracking `main` keeps scanning `main` independently.
  [Claude submission and review rules](https://claude.com/docs/plugins/submit).
- **OpenAI:** use **With MCP**, `https://mcp.wimbly.ai/mcp`, the public submission
  ZIP and the verified Wimbly publisher in [the portal](https://platform.openai.com/plugins).
  Enter dedicated reviewer credentials only there. Package updates require
  upload, review and publication; eligible hosted MCP updates are scanned after
  initial publication. Keep the server URL stable.
  [OpenAI submission and update rules](https://developers.openai.com/plugins/deploy/submission).

## Release checks and retries

Follow the [release steps](README.md#release). The tagged source must include
the release scripts. The manual delivery workflow runs from `main`, checks out
the selected tag and requires an existing published GitHub release candidate.
Drafts and missing releases refuse. It verifies merged ancestry, both manifest
versions, the remote tag and archive checksums, then marks the candidate stable
and advances `directory-release` through a normal fast-forward push.

Existing assets are verified byte for byte and never clobbered. History rewrites,
version reductions and older candidates refuse. Runs are serialized. If delivery
fails after the GitHub candidate became stable, rerun with the same tag to finish;
already-stable candidates are not republished. Prepare assets before making
a release immutable. Branch protection is never overridden.

Promotion requires a passing public preflight for the same source within 15
minutes. It checks resource/issuer discovery, PKCE/CIMD, authentication challenges
and private-route fences. It makes no authenticated tool calls; actual OAuth,
tool behavior and UI still need host testing. Backend deployment uses the
Wimbly application's separate release workflow.

Native marketplace installations follow `main`. To update and restart the client:

```text
claude plugin update wimbly@wimbly
codex plugin marketplace upgrade wimbly
```
