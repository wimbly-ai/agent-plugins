#!/usr/bin/env python3
"""Prepare a local review page without submitting, publishing or invoking tools."""

import argparse
import base64
import json
import re
import subprocess
from html import escape
from pathlib import Path
from string import Template
from zipfile import ZipFile

from prepare_release import prepare
from validate import MCP_URL, ROOT


def tool_snapshot(path):
    if path is None:
        return {"status": "not_captured", "tools": []}
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Use a tools/list metadata response smaller than 1 MiB")
    capture = json.loads(path.read_text())
    if not isinstance(capture, dict) or "error" in capture:
        raise ValueError("Expected a successful tools/list response")
    if capture.get("resource", MCP_URL) != MCP_URL:
        raise ValueError("Tool metadata must belong to the canonical Wimbly resource")
    result = capture.get("result", capture)
    tools = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(tools, list) or not 0 < len(tools) <= 200:
        raise ValueError("Expected 1–200 tools from tools/list")
    if result.get("nextCursor"):
        raise ValueError("Capture all tools/list pages before reviewing the inventory")
    selected, names = [], set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("Each tool must contain metadata")
        name = tool.get("name")
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]{1,128}", name
        ):
            raise ValueError("Tool names must follow the MCP name format")
        if name in names:
            raise ValueError("Tool names must be unique")
        names.add(name)
        item = {"name": name}
        for key in ("title", "description"):
            if key in tool:
                if not isinstance(tool[key], str):
                    raise ValueError(f"Tool {key} must be text")
                item[key] = tool[key]
        for key in ("inputSchema", "outputSchema"):
            if key in tool:
                if not isinstance(tool[key], dict):
                    raise ValueError(f"Tool {key} must be an object")
                item[key] = tool[key]
        annotations = tool.get("annotations", {})
        if not isinstance(annotations, dict):
            raise ValueError("Tool annotations must be an object")
        item["annotations"] = {}
        for key in (
            "title",
            "readOnlyHint",
            "destructiveHint",
            "openWorldHint",
            "idempotentHint",
        ):
            if key in annotations:
                value = annotations[key]
                if (key == "title" and not isinstance(value, str)) or (
                    key != "title" and type(value) is not bool
                ):
                    raise ValueError("Invalid tool annotation: " + key)
                item["annotations"][key] = value
        selected.append(item)
    # Only advertised tool definitions survive. No auth, result payloads or
    # arbitrary top-level capture fields are copied into the review artifacts.
    return {
        "status": "provided_snapshot",
        "sourceVerified": False,
        "tools": sorted(selected, key=lambda tool: tool["name"]),
    }


def render(review, root=ROOT):
    def image(name):
        mime = "image/svg+xml" if name.endswith(".svg") else "image/png"
        encoded = base64.b64encode(
            (root / name.removeprefix("./")).read_bytes()
        ).decode()
        return f"data:{mime};base64,{encoded}"

    def text(value):
        return escape(str(value), quote=True)

    def details(label, value):
        return f"<details><summary>{text(label)}</summary><pre>{text(value)}</pre></details>"

    listing = review["listing"]
    snapshot = review["toolInventory"]
    tools = snapshot["tools"]
    tool_cards = []
    for tool in tools:
        annotations = tool["annotations"]
        title = tool.get("title") or annotations.get("title") or "No title declared"
        flags = " · ".join(
            f"{name}: {str(annotations[name]).lower() if name in annotations else 'not declared'}"
            for name in (
                "readOnlyHint",
                "destructiveHint",
                "openWorldHint",
                "idempotentHint",
            )
        )
        schemas = {
            key: tool[key] for key in ("inputSchema", "outputSchema") if key in tool
        }
        tool_cards.append(
            f'<article class="tool"><h3>{text(title)}</h3><code>{text(tool["name"])}</code>'
            f'<p class="description">{text(tool.get("description", "No description declared"))}</p>'
            f'<p class="muted flags">{text(flags)}</p>'
            + details("Input and output schemas", json.dumps(schemas, indent=2))
            + "</article>"
        )
    if tools:
        inventory = (
            f"<p>{len(tools)} definitions from the supplied tools/list snapshot.</p>"
            '<p class="muted">This file does not verify the snapshot\'s origin, freshness, '
            "account capabilities or provider approval. Compare it with the signed-in server. "
            "Annotation hints describe behavior; they are not permission enforcement.</p>"
            + "".join(tool_cards)
        )
    else:
        inventory = (
            "<p><strong>Live tool inventory has not been captured.</strong></p>"
            "<p>The ZIP points at the MCP server; it does not contain the server's tool list. "
            "Sign in with MCP Inspector and select Tools → List Tools, or open "
            "MCPs → Wimbly in the OpenAI publisher draft. Review names, titles, descriptions, "
            "schemas and annotation hints there before submission.</p>"
            '<p class="muted">This preview makes no authenticated requests or tool calls.</p>'
        )
    archives = "".join(
        f"<details><summary>{text(name)} · {len(archive['files'])} files</summary>"
        f'<p class="muted">SHA256: <code>{text(archive["sha256"])}</code></p>'
        "<ul>"
        + "".join(f"<li><code>{text(name)}</code></li>" for name in archive["files"])
        + "</ul></details>"
        for name, archive in review["archives"].items()
    )
    source = review["source"]
    values = {
        "name": text(listing["displayName"]),
        "version": text(review["version"]),
        "author": text(listing["developerName"]),
        "manifest_author": text(review["manifestAuthor"]),
        "description": text(listing["shortDescription"]),
        "long_description": text(listing["longDescription"]),
        "logo": image(listing["logo"]),
        "small_light": image(listing["composerIcon"]),
        "small_dark": image(listing["composerIconDark"]),
        "slug": text(review["slug"]),
        "resource": text(review["resource"]),
        "commit": text(source["commit"]),
        "source_state": "Uncommitted changes included"
        if source["dirty"]
        else "Committed source",
        "capabilities": text(", ".join(listing["capabilities"])),
        "prompts": "".join(
            f"<li>{text(prompt)}</li>" for prompt in listing["defaultPrompt"]
        ),
        "skill": details(
            "Read the complete onboarding skill", review["onboardingSkill"]
        ),
        "review_tools": ", ".join(
            f"<code>{text(name)}</code>" for name in review["reviewCaseTools"]
        ),
        "inventory": inventory,
        "archives": archives,
        "review_cases": details(
            "Read the submitted review cases",
            json.dumps(review["reviewCases"], indent=2),
        ),
    }
    return Template((root / "scripts/review.html").read_text()).substitute(values)


def preview(output, tag=None, check_live=False, tools_json=None, root=ROOT):
    output = output.resolve()
    for name in ("review.html", "review.json", "review.md"):
        (output / name).unlink(missing_ok=True)
    snapshot = tool_snapshot(tools_json)
    manifest = prepare(output, tag=tag, check_live=check_live, root=root)
    plugin = json.loads((root / "plugin.json").read_text())
    extension = plugin["extensions"]["com.openai"]
    archives = {}
    for name, digest in manifest["artifacts"].items():
        with ZipFile(output / name) as archive:
            archives[name] = {"sha256": digest, "files": archive.namelist()}
    review = {
        "previewOnly": True,
        "version": manifest["version"],
        "source": {
            "commit": manifest["sourceCommit"],
            "dirty": manifest["sourceDirty"],
        },
        "slug": plugin["name"],
        "manifestAuthor": plugin["author"]["name"],
        "listing": extension["interface"],
        "resource": MCP_URL,
        "onboardingSkill": (root / "skills/onboarding/SKILL.md").read_text(),
        "reviewCases": extension["review"]["test_cases"],
        "reviewCaseTools": sorted(
            {
                case["tools_triggered"]
                for case in extension["review"]["test_cases"]["positive"]
            }
        ),
        "toolInventory": snapshot,
        "archives": archives,
    }
    (output / "review.json").write_text(json.dumps(review, indent=2) + "\n")
    (output / "review.html").write_text(render(review, root))
    summary = (
        f"## Preview: {review['listing']['displayName']} {review['version']}\n\n"
        f"- Developer: {review['listing']['developerName']}\n"
        f"- MCP: `{MCP_URL}`\n"
        f"- Source: `{manifest['sourceCommit']}`\n"
        "- Download the **wimbly-release-preview** artifact and open **review.html**.\n"
        "- The review includes branding, prompts, skill, package files and checksums.\n"
        "- Live tools require a signed-in tools/list capture; none is inferred from the ZIP.\n\n"
        "**Preview only:** no submission, release, directory update or authenticated tool call.\n"
    )
    (output / "review.md").write_text(summary)
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--tag")
    parser.add_argument("--check-live", action="store_true")
    parser.add_argument(
        "--tools-json",
        type=Path,
        help="Optional tools/list metadata JSON; never an auth/session export",
    )
    args = parser.parse_args()
    try:
        review = preview(args.output_dir, args.tag, args.check_live, args.tools_json)
        print(f"Preview only: {args.output_dir / 'review.html'}")
        print(f"Tool inventory: {review['toolInventory']['status']}")
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as error:
        raise SystemExit(f"Release preview failed: {error}")
