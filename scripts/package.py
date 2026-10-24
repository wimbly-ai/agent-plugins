#!/usr/bin/env python3
"""Build a reproducible release ZIP from the validated, explicit file list."""

import argparse
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from validate import FILES, ROOT, validate


def openai_app_id(value):
    if not re.fullmatch(
        r"(?:asdk_app_|connector_|templated_apps_)[A-Za-z0-9][A-Za-z0-9_-]*", value
    ):
        raise argparse.ArgumentTypeError(
            "Use a registered asdk_app_, connector_, or templated_apps_ ID, "
            "not a plugin_ UI route ID"
        )
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="ZIP destination (default: dist/wimbly-<version>[-chatgpt].zip)",
    )
    parser.add_argument(
        "--tag", help="Require a release tag matching the manifest version"
    )
    host = parser.add_mutually_exclusive_group()
    host.add_argument(
        "--openai-app-id",
        type=openai_app_id,
        help="Build a portable-only ChatGPT ZIP bound to this registered MCP server",
    )
    host.add_argument(
        "--openai-submission",
        action="store_true",
        help="Build the public OpenAI submission ZIP, without a private app mapping",
    )
    args = parser.parse_args()
    version = validate()
    if args.tag is not None and args.tag != f"v{version}":
        raise ValueError(f"Tag {args.tag} does not match manifest version {version}")
    portable = bool(args.openai_app_id or args.openai_submission)
    suffix = (
        "-openai-submission"
        if args.openai_submission
        else "-chatgpt"
        if args.openai_app_id
        else ""
    )
    destination = (
        args.output or ROOT / "dist" / f"wimbly-{version}{suffix}.zip"
    ).resolve()
    if destination.suffix != ".zip" or destination in (ROOT / name for name in FILES):
        raise ValueError("Choose a .zip destination outside the release file list")
    files = {name: (ROOT / name).read_bytes() for name in FILES}
    if args.openai_submission:
        plugin = json.loads(files["plugin.json"])
        extension = plugin["extensions"]["com.openai"]
        if "apps" in extension or "hooks" in extension or "hooks" in plugin:
            raise ValueError("Public submissions cannot contain app mappings or hooks")
    if portable:
        files = {
            name: data
            for name, data in files.items()
            if name in ("plugin.json", "mcp.json", "README.md", "LICENSE")
            or name.startswith(("skills/", "assets/"))
        }
    if args.openai_app_id:
        plugin = json.loads(files["plugin.json"])
        plugin["extensions"]["com.openai"]["apps"] = "./.app.json"
        files["plugin.json"] = (json.dumps(plugin, indent=2) + "\n").encode("utf-8")
        mapping = {"apps": {"wimbly": {"id": args.openai_app_id, "required": True}}}
        files[".app.json"] = (json.dumps(mapping, indent=2) + "\n").encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(
        destination, "w", compression=ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(files):
            archive_name = name if portable else f"wimbly/{name}"
            info = ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                files[name],
                compress_type=ZIP_DEFLATED,
                compresslevel=9,
            )
    print(f"Packaged Wimbly {version}: {len(files)} files, {destination}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"Packaging failed: {error}")
