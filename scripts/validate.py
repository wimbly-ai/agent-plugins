#!/usr/bin/env python3
"""Check the Wimbly package without fetching dependencies or calling the service."""

import json
import re
import struct
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SETUP_URL = "https://mcp.wimbly.ai/mcp/setup"
FILES = (
    "plugin.json",
    "mcp.json",
    ".mcp.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    "skills/onboarding/SKILL.md",
    "skills/onboarding/agents/openai.yaml",
    "assets/logo.png",
    "assets/composer.png",
    "README.md",
    "LICENSE",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(root=ROOT):
    root = root.resolve()
    for name in FILES:
        path = root / name
        require(path.is_file(), f"Missing file: {name}")
        require(path.resolve().is_relative_to(root), f"Path escapes package: {name}")
        require(
            not any(
                part.is_symlink() for part in (path, *path.parents) if part != root
            ),
            f"Release files must not use symlinks: {name}",
        )

    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8"))

    plugin = read("plugin.json")
    claude = read(".claude-plugin/plugin.json")
    require(plugin["name"] == "wimbly", "Plugin name must be wimbly")
    require(
        plugin["$schema"]
        == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "Unexpected portable manifest schema",
    )
    require(
        re.fullmatch(r"\d+\.\d+\.\d+(?:-[\w.-]+)?", plugin["version"]),
        "Invalid version",
    )
    for key in (
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
    ):
        require(plugin[key] == claude[key], f"Manifests disagree on {key}")

    for name, transport in (("mcp.json", "streamable-http"), (".mcp.json", "http")):
        config = read(name)
        server = {"type": transport, "url": SETUP_URL}
        require(
            config["mcpServers"] == {"wimbly-setup": server},
            f"{name} must expose only the setup resource, without credentials",
        )
    require(
        read("mcp.json")["$schema"]
        == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "Unexpected portable MCP schema",
    )

    extension = plugin["extensions"]["com.openai"]
    require(
        extension["onboardingSkill"] == "./skills/onboarding/SKILL.md",
        "Wrong onboarding path",
    )
    cases = extension["review"]["test_cases"]
    for kind, count in (("positive", 5), ("negative", 3)):
        require(len(cases[kind]) == count, f"Expected {count} {kind} review cases")
        for case in cases[kind]:
            for field in ("description", "prompt", "expected_behavior"):
                require(
                    isinstance(case.get(field), str) and case[field].strip(),
                    f"Review case needs {field}",
                )
            if kind == "positive":
                require(
                    case.get("tools_triggered") == "get_setup_status",
                    "Onboarding review cases must use get_setup_status",
                )
    listing = extension["interface"]
    for field, limit in (
        ("displayName", 30),
        ("shortDescription", 30),
        ("longDescription", 4000),
        ("developerName", 80),
    ):
        value = listing[field]
        require(isinstance(value, str) and 0 < len(value) <= limit, f"Invalid {field}")
    for field in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
        url = urlsplit(listing[field])
        require(
            url.scheme == "https"
            and url.hostname
            and not url.username
            and not url.password,
            f"Invalid {field}",
        )
    for field, other in (
        ("supportURL", "supportUrl"),
        ("privacyPolicyURL", "privacyPolicyUrl"),
        ("termsOfServiceURL", "termsOfServiceUrl"),
    ):
        require(listing[field] == claude[other], f"Listing links disagree on {field}")
    require(listing["logo"] == claude["icon"], "Listing icons disagree")
    for field in ("logo", "composerIcon"):
        name = listing[field]
        require(name.startswith("./") and name[2:] in FILES, f"Unpackaged {field}")
        data = (root / name).read_bytes()
        require(
            data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24,
            f"Invalid PNG: {name}",
        )
        width, height = struct.unpack(">II", data[16:24])
        require(
            48 <= width == height <= 4096 and len(data) <= 5 * 1024 * 1024,
            f"Invalid icon dimensions or size: {name}",
        )

    for name in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
        catalog = read(name)
        require(
            catalog["name"] == "wimbly" and len(catalog["plugins"]) == 1,
            f"Invalid catalog: {name}",
        )
        entry = catalog["plugins"][0]
        require(entry["name"] == plugin["name"], f"Wrong plugin in {name}")
        source = (
            "./" if name.startswith(".claude") else {"source": "local", "path": "./"}
        )
        require(
            entry["source"] == source, f"Catalog must point at the package root: {name}"
        )

    skill = (root / "skills/onboarding/SKILL.md").read_text(encoding="utf-8")
    require(
        skill.startswith("---\nname: onboarding\n") and "\n---\n" in skill[4:],
        "Invalid skill frontmatter",
    )
    metadata = (root / "skills/onboarding/agents/openai.yaml").read_text(
        encoding="utf-8"
    )
    urls = re.findall(r'^\s+url: "([^"]+)"$', metadata, re.MULTILINE)
    require(urls == [SETUP_URL], "Skill dependency must use the setup resource")
    return plugin["version"]


if __name__ == "__main__":
    try:
        version = validate()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Validation failed: {error}")
    print(f"Validated Wimbly {version}: {len(FILES)} release files")
