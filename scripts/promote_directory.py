#!/usr/bin/env python3
"""Advance Claude's tracked branch from a verified stable GitHub release."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from validate import ROOT

REPOSITORY = "wimbly-ai/agent-plugins"
BRANCH = "directory-release"
VERSION = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"


def stable_version(version):
    match = re.fullmatch(VERSION, version)
    if not match:
        raise ValueError(
            "Directory releases require a stable major.minor.patch version"
        )
    return tuple(map(int, match.groups()))


def github_release(tag):
    return json.loads(
        subprocess.check_output(
            [
                "gh",
                "release",
                "view",
                tag,
                "--repo",
                REPOSITORY,
                "--json",
                "tagName,isDraft,isPrerelease,publishedAt",
            ],
            cwd=ROOT,
            text=True,
        )
    )


def promote(
    event,
    expected_sha,
    artifact_dir,
    apply=False,
    root=ROOT,
    *,
    event_name=None,
    workflow_ref=None,
    read_release=github_release,
):
    if (
        event_name != "workflow_dispatch"
        or workflow_ref != "refs/heads/main"
        or event.get("repository", {}).get("full_name") != REPOSITORY
    ):
        raise ValueError(
            "Only an explicit workflow dispatch from main in the plugin repository can promote"
        )
    tag = event.get("inputs", {}).get("tag", "")
    if not isinstance(tag, str) or not tag.startswith("v"):
        raise ValueError("Expected a v-prefixed release tag")
    version = tag[1:]
    next_version = stable_version(version)
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("Expected the full release commit SHA")

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    source = git("rev-parse", "HEAD")
    if (
        source != expected_sha
        or git("rev-parse", f"refs/tags/{tag}^{{commit}}") != source
    ):
        raise ValueError("The checkout, release tag and selected source SHA must agree")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Directory promotion requires a clean checkout")
    plugin = json.loads((root / "plugin.json").read_text())
    claude = json.loads((root / ".claude-plugin/plugin.json").read_text())
    if plugin["version"] != version or claude["version"] != version:
        raise ValueError("Release tag and both plugin versions must agree")

    manifest = json.loads((artifact_dir / "release.json").read_text())
    if (
        manifest.get("sourceCommit") != source
        or manifest.get("sourceDirty") is not False
        or manifest.get("version") != version
    ):
        raise ValueError(
            "Prepared artifacts need matching source and a passing public preflight"
        )
    preflight = json.loads((artifact_dir / "preflight.json").read_text())
    created = datetime.fromisoformat(preflight["createdAt"])
    if (
        preflight.get("sourceCommit") != source
        or not preflight.get("checks")
        or created.utcoffset() is None
        or not 0 <= (datetime.now(timezone.utc) - created).total_seconds() <= 900
    ):
        raise ValueError("A fresh passing public preflight for this commit is required")
    artifacts = manifest["artifacts"]
    expected_names = {
        f"wimbly-{version}.zip",
        f"wimbly-{version}-openai-submission.zip",
    }
    if set(artifacts) != expected_names:
        raise ValueError("Expected exactly the two public directory archives")
    for name, digest in artifacts.items():
        if hashlib.sha256((artifact_dir / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Prepared release archive checksum mismatch")

    release = read_release(tag)
    if (
        not isinstance(release, dict)
        or release.get("tagName") != tag
        or release.get("isDraft") is not False
        or type(release.get("isPrerelease")) is not bool
        or not release.get("publishedAt")
    ):
        raise ValueError("A matching published GitHub release candidate is required")
    if apply and release["isPrerelease"]:
        raise ValueError(
            "Mark the verified candidate stable before applying directory promotion"
        )

    git("fetch", "--no-tags", "origin", "+refs/heads/main:refs/remotes/origin/main")
    tags = dict(
        (ref, sha)
        for sha, ref in (
            line.split()
            for line in git(
                "ls-remote",
                "--tags",
                "origin",
                f"refs/tags/{tag}",
                f"refs/tags/{tag}^{{}}",
            ).splitlines()
        )
    )
    if tags.get(f"refs/tags/{tag}^{{}}", tags.get(f"refs/tags/{tag}")) != source:
        raise ValueError("The remote release tag changed or is missing")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, "origin/main"], cwd=root
    ).returncode:
        raise ValueError("Release commit must already belong to main")
    previous = git("ls-remote", "--heads", "origin", f"refs/heads/{BRANCH}")
    if previous:
        git(
            "fetch",
            "--no-tags",
            "origin",
            f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}",
        )
        previous = git("rev-parse", f"origin/{BRANCH}")
        if previous == source:
            return {"status": "already_promoted", "branch": BRANCH, "commit": source}
        if subprocess.run(
            ["git", "merge-base", "--is-ancestor", previous, source], cwd=root
        ).returncode:
            raise ValueError(
                "Directory branch cannot move backwards or across histories"
            )
        previous_manifest = json.loads(git("show", f"{previous}:plugin.json"))
        if next_version <= stable_version(previous_manifest["version"]):
            raise ValueError("Directory releases must increase the plugin version")
    if apply:
        # Deliberately no force: a concurrent newer release must win.
        git("push", "origin", f"{source}:refs/heads/{BRANCH}")
    return {
        "status": "promoted_for_claude_scan" if apply else "dry_run",
        "branch": BRANCH,
        "commit": source,
        "directoryPublicationVerified": False,
        "openai": "Upload the OpenAI submission ZIP in the existing plugin portal",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, type=Path)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            promote(
                json.loads(args.event.read_text()),
                args.expected_sha,
                args.artifact_dir,
                args.apply,
                event_name=os.environ.get("GITHUB_EVENT_NAME"),
                workflow_ref=os.environ.get("GITHUB_REF"),
            ),
            indent=2,
        )
    )


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
        raise SystemExit(f"Directory promotion failed: {error}")
