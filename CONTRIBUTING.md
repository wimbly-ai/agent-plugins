# Contributing

Python 3.12+; no Python dependencies.

## Check and preview

```sh
python3 scripts/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/preview_release.py --check-live
open dist/review.html
```

Packages, checksums and the review page are written to `dist/`.

## Inspect tools

Launch [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

```sh
npx @modelcontextprotocol/inspector --server-url https://mcp.wimbly.ai/mcp --transport http
```

Sign in → **Tools → List Tools**. Inspect names, titles, descriptions, schemas and annotations.
To include the complete `tools/list` JSON response in the preview:

```sh
python3 scripts/preview_release.py --tools-json /tmp/wimbly-tools.json
```

Use metadata only, never an auth/session export. [Host testing instructions](https://developers.openai.com/plugins/deploy/connect-chatgpt).

## Private ChatGPT install

Register a custom MCP server, then build with its actual app ID:

```sh
python3 scripts/package.py --openai-app-id "$OPENAI_APP_ID"
```

Use `asdk_app_`, `connector_` or `templated_apps_`; remove the `plugin_` route
prefix. Upload `dist/wimbly-<version>-chatgpt.zip` for private tests. Public
submission uses `wimbly-<version>-openai-submission.zip`.

## Release and retry

Follow the [release steps](README.md#release). For a partial delivery, rerun the
same tag; don't overwrite assets or rewrite tags. Public discovery checks don't
replace signed-in host tests. Keep credentials out of the repository.

- [Claude submission and tracked-branch setup](https://claude.com/docs/plugins/submit)
- [OpenAI submission and updates](https://developers.openai.com/plugins/deploy/submission)
- [Release safeguards](scripts/promote_directory.py)

## Directory review

Before submitting in the [OpenAI portal](https://platform.openai.com/plugins),
complete **Review information**: run the five positive and three negative cases
with the dedicated reviewer account, add a reviewer-accessible genuine demo
video, and enter credentials privately in the portal. The ZIP contains no
passwords. Fields marked as ZIP-managed must be changed in `plugin.json`; use
`extensions.com.openai.review.demo_recording_url` for the video URL.

A successful public preflight or ZIP upload does not complete these steps.
Review the prepared draft before selecting **Submit for review**.
