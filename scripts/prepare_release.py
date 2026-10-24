#!/usr/bin/env python3
"""Build both directory archives, checksums and a truthful publication handoff."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from check_mcp import check
from validate import ROOT, validate


def prepare(output, tag=None, check_live=False, root=ROOT):
    version = validate(root)
    if tag is not None and tag != f"v{version}":
        raise ValueError("Release tag must match both plugin manifest versions")
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            text=True,
        ).strip()
    )
    if tag and dirty:
        raise ValueError("Commit tracked changes before preparing a tagged release")
    output = output.resolve()
    # A failed or offline run must not leave an earlier successful check reusable.
    (output / "preflight.json").unlink(missing_ok=True)
    preflight = check() if check_live else None
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    for suffix, flags in (("", []), ("-openai-submission", ["--openai-submission"])):
        archive = output / f"wimbly-{version}{suffix}.zip"
        command = [sys.executable, str(root / "scripts/package.py"), *flags]
        if tag:
            command += ["--tag", tag]
        subprocess.run(command + ["--output", str(archive)], check=True, cwd=root)
        files[archive.name] = hashlib.sha256(archive.read_bytes()).hexdigest()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    manifest = {
        "version": version,
        "sourceCommit": commit,
        "sourceDirty": dirty,
        "artifacts": files,
        "openai": {
            "status": "portal_upload_required",
            "archive": f"wimbly-{version}-openai-submission.zip",
            "portal": "https://platform.openai.com/plugins",
            "documentation": "https://developers.openai.com/plugins/deploy/submission",
            "hostedMcpUpdates": "Automatically scanned after initial publication",
        },
        "claude": {
            "delivery": "manual_workflow_then_tracked_branch",
            "archive": f"wimbly-{version}.zip",
            "repository": "https://github.com/wimbly-ai/agent-plugins",
            "trackedBranch": "directory-release",
            "portal": "https://claude.ai/directory/manage",
            "documentation": "https://claude.com/docs/plugins/submit",
            "publication": "Subject to first review and the portal auto-publish setting",
        },
    }
    (output / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(files.items()))
    )
    if preflight is not None:
        (output / "preflight.json").write_text(
            json.dumps(
                {
                    **preflight,
                    "sourceCommit": commit,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            )
            + "\n"
        )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--tag")
    parser.add_argument("--check-live", action="store_true")
    args = parser.parse_args()
    manifest = prepare(args.output_dir, args.tag, args.check_live)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as error:
        raise SystemExit(f"Release preparation failed: {error}")
