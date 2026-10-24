# Wimbly

Growth engine for legal and financial services. Connect your Wimbly account to
use its tools and guided onboarding in your agent.

## Install

**Claude Code**

```text
/plugin marketplace add wimbly-ai/agent-plugins
/plugin install wimbly@wimbly
```

Then run `/wimbly:onboarding`.

**Codex**

```sh
codex plugin marketplace add wimbly-ai/agent-plugins
codex plugin add wimbly@wimbly
```

Then run `$onboarding`. Sign in to Wimbly when prompted.

## Preview before sending

1. Open [Preview plugin release](https://github.com/wimbly-ai/agent-plugins/actions/workflows/preview-release.yml)
   → **Run workflow**. Choose a branch or enter a version tag.
2. Download **wimbly-release-preview**, unzip it, and open **review.html**.
3. Inspect live tools in the [OpenAI portal](https://platform.openai.com/plugins)
   → **Wimbly → MCPs → Wimbly** after signing in. The ZIP doesn't contain the tool list.

## Release

1. Bump versions in [plugin.json](plugin.json) and
   [.claude-plugin/plugin.json](.claude-plugin/plugin.json), merge to `main`, and
   push a matching `vX.Y.Z` tag. CI creates a [GitHub prerelease](https://github.com/wimbly-ai/agent-plugins/releases).
2. Preview that tag using the steps above.
3. Open [Release to plugin directories](https://github.com/wimbly-ai/agent-plugins/actions/workflows/directory-release.yml)
   → **Run workflow**. Choose `main` and enter the reviewed tag.
4. In the [OpenAI portal](https://platform.openai.com/plugins), upload
   `wimbly-<version>-openai-submission.zip` to Wimbly, then complete review and publication.

For Claude, set **Settings → Tracked branch or tag** to `directory-release` in
the [Claude portal](https://claude.ai/directory/manage). Publication follows its review settings.

The workflow buttons become available after this automation merges to `main`.
Previewing publishes nothing; backend deployment is separate.

[Local commands, private installs and troubleshooting](https://github.com/wimbly-ai/agent-plugins/blob/main/CONTRIBUTING.md)
· [Support](https://www.wimbly.ai/contact)
· [Privacy](https://www.wimbly.ai/legal-pages/privacy-policy)
· [Terms](https://www.wimbly.ai/legal-pages/terms-conditions)
