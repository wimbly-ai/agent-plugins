#!/usr/bin/env python3
"""Attach missing release files; verify and preserve files already published."""

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from validate import ROOT


def gh(*args):
    return subprocess.check_output(["gh", *args], cwd=ROOT, text=True)


def attach(tag, artifact_dir, run_gh=gh):
    manifest = json.loads((artifact_dir / "release.json").read_text())
    version = manifest["version"]
    if tag != f"v{version}" or manifest.get("sourceDirty") is not False:
        raise ValueError("Release assets require the matching tag and clean source")
    expected = {f"wimbly-{version}.zip", f"wimbly-{version}-openai-submission.zip"}
    if set(manifest["artifacts"]) != expected:
        raise ValueError("Expected both directory archives")
    for name, digest in manifest["artifacts"].items():
        if hashlib.sha256((artifact_dir / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Local release archive checksum mismatch")
    files = sorted(expected | {"SHA256SUMS", "release.json"})
    for name in files:
        if not (artifact_dir / name).is_file():
            raise ValueError("Release asset is missing: " + name)
    checksums = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(manifest["artifacts"].items())
    )
    if (artifact_dir / "SHA256SUMS").read_text() != checksums:
        raise ValueError("SHA256SUMS must match the prepared archives")
    existing = {
        a["name"]
        for a in json.loads(run_gh("release", "view", tag, "--json", "assets"))[
            "assets"
        ]
    }
    # Verify all existing files before uploading any missing ones. No --clobber.
    with tempfile.TemporaryDirectory(prefix="wimbly-release-download-") as directory:
        for name in files:
            if name in existing:
                run_gh(
                    "release", "download", tag, "--pattern", name, "--dir", directory
                )
                if (Path(directory) / name).read_bytes() != (
                    artifact_dir / name
                ).read_bytes():
                    raise ValueError("Published release asset differs: " + name)
    for name in files:
        if name not in existing:
            run_gh("release", "upload", tag, str(artifact_dir / name))
    return {
        "verifiedExisting": sorted(set(files).intersection(existing)),
        "uploaded": [name for name in files if name not in existing],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        print(json.dumps(attach(args.tag, args.artifact_dir), indent=2))
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.CalledProcessError,
    ) as error:
        raise SystemExit(f"Release assets failed: {error}")
