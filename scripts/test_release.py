"""Release checks use temporary repositories and no publisher credentials."""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import check_mcp
import prepare_release
from attach_release_assets import attach
from promote_directory import BRANCH, REPOSITORY, promote, stable_version
from validate import FILES, MCP_URL, ROOT


def discovery(url, method="GET", body=None, headers=None):
    if url == check_mcp.METADATA:
        return (
            200,
            {},
            json.dumps(
                {"resource": MCP_URL, "authorization_servers": [check_mcp.ISSUER]}
            ).encode(),
        )
    if url == MCP_URL:
        if method != "POST" or b'"initialize"' not in body:
            raise AssertionError("Preflight must use anonymous initialize only")
        if headers.get("Authorization") not in (
            None,
            "Bearer invalid-release-preflight",
        ):
            raise AssertionError("Preflight must not use real credentials")
        return (
            401,
            {"www-authenticate": f'Bearer resource_metadata="{check_mcp.METADATA}"'},
            b"",
        )
    if url.startswith(check_mcp.ISSUER):
        return (
            200,
            {},
            json.dumps(
                {
                    "issuer": check_mcp.ISSUER,
                    "code_challenge_methods_supported": ["S256"],
                    "client_id_metadata_document_supported": True,
                }
            ).encode(),
        )
    return 404, {}, b""


class DiscoveryTests(unittest.TestCase):
    def test_public_preflight_has_no_authenticated_tool_calls(self):
        result = check_mcp.check(discovery)
        self.assertEqual(result["authenticatedToolCalls"], 0)
        self.assertEqual(len(result["checks"]), 14)

    def test_bad_resource_or_issuer_is_refused(self):
        for field, value in (
            ("resource", "https://old.invalid/mcp"),
            ("authorization_servers", ["https://dev.invalid"]),
        ):
            with self.subTest(field=field):

                def wrong(url, **kwargs):
                    status, headers, data = discovery(url, **kwargs)
                    if url == check_mcp.METADATA:
                        parsed = json.loads(data)
                        parsed[field] = value
                        data = json.dumps(parsed).encode()
                    return status, headers, data

                with self.assertRaises(ValueError):
                    check_mcp.check(wrong)

    def test_anonymous_access_or_wrong_challenge_is_refused(self):
        for status, headers in ((200, {}), (302, {}), (401, {})):
            with self.subTest(status=status, headers=headers):

                def wrong(url, **kwargs):
                    return (
                        (status, headers, b"")
                        if url == MCP_URL
                        else discovery(url, **kwargs)
                    )

                with self.assertRaises(ValueError):
                    check_mcp.check(wrong)

    def test_missing_cimd_or_pkce_is_refused(self):
        for field in (
            "code_challenge_methods_supported",
            "client_id_metadata_document_supported",
        ):
            with self.subTest(field=field):

                def wrong(url, **kwargs):
                    status, headers, data = discovery(url, **kwargs)
                    if url.startswith(check_mcp.ISSUER):
                        parsed = json.loads(data)
                        del parsed[field]
                        data = json.dumps(parsed).encode()
                    return status, headers, data

                with self.assertRaises(ValueError):
                    check_mcp.check(wrong)

    def test_public_private_route_is_refused(self):
        def wrong(url, **kwargs):
            return (
                (200, {}, b"")
                if url.endswith("/v1/auth/me")
                else discovery(url, **kwargs)
            )

        with self.assertRaisesRegex(ValueError, "private or retired"):
            check_mcp.check(wrong)


class HttpTransportTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        requests = self.requests

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/must-not-follow")
                    self.end_headers()
                elif self.path == "/large":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"x" * 65537)
                else:
                    self.send_response(401)
                    self.end_headers()

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.origin = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_real_http_errors_are_observed_and_redirects_are_not_followed(self):
        self.assertEqual(check_mcp.fetch(self.origin + "/unauthorized")[0], 401)
        self.assertEqual(check_mcp.fetch(self.origin + "/redirect")[0], 302)
        self.assertNotIn("/must-not-follow", self.requests)

    def test_real_oversized_response_is_refused(self):
        with self.assertRaisesRegex(ValueError, "64 KiB"):
            check_mcp.fetch(self.origin + "/large")


class Project(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="wimbly-release-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        for name in (*FILES, ".gitignore"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        for name in ("validate.py", "package.py", "check_mcp.py", "prepare_release.py"):
            target = self.root / "scripts" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "scripts" / name, target)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Release fixture")
        self.git("config", "user.email", "release-fixture@example.test")
        # These are throwaway fixture commits, never repository release commits.
        self.git("config", "commit.gpgsign", "false")
        self.git("add", ".")
        self.git("commit", "-m", "Initial release fixture")
        self.version = json.loads((self.root / "plugin.json").read_text())["version"]
        self.output = self.base / "artifacts"

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL
        ).strip()

    def package(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts/package.py"), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )


class PackageTests(Project):
    def test_public_openai_archive_has_one_manifest_and_no_app_mapping(self):
        output = self.base / "public.zip"
        result = self.package("--openai-submission", "--output", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        with ZipFile(output) as archive:
            names = archive.namelist()
            self.assertIn("plugin.json", names)
            self.assertIn("mcp.json", names)
            self.assertEqual(sum(n.endswith("plugin.json") for n in names), 1)
            self.assertNotIn(".app.json", names)
            self.assertFalse(
                any(
                    n.startswith((".claude-plugin/", ".agents/", "wimbly/"))
                    for n in names
                )
            )
            self.assertNotIn(
                "apps",
                json.loads(archive.read("plugin.json"))["extensions"]["com.openai"],
            )
            for name in names:
                self.assertEqual(archive.read(name), (self.root / name).read_bytes())

    def test_default_universal_and_private_mapping_remain_available(self):
        for flags, name in (
            ([], f"wimbly-{self.version}.zip"),
            (
                ["--openai-app-id", "asdk_app_fixture"],
                f"wimbly-{self.version}-chatgpt.zip",
            ),
        ):
            with self.subTest(flags=flags):
                result = self.package(*flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                with ZipFile(self.root / "dist" / name) as archive:
                    if flags:
                        self.assertEqual(
                            json.loads(archive.read(".app.json"))["apps"]["wimbly"][
                                "id"
                            ],
                            "asdk_app_fixture",
                        )
                    else:
                        self.assertEqual(
                            set(archive.namelist()), {"wimbly/" + n for n in FILES}
                        )

    def test_private_mapping_cannot_be_combined_with_submission(self):
        output = self.base / "should-not-exist.zip"
        result = self.package(
            "--openai-submission",
            "--openai-app-id",
            "asdk_app_fixture",
            "--output",
            str(output),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())

    def test_unsafe_public_app_reference_is_refused(self):
        path = self.root / "plugin.json"
        plugin = json.loads(path.read_text())
        plugin["extensions"]["com.openai"]["apps"] = "./.app.json"
        path.write_text(json.dumps(plugin))
        result = self.package("--openai-submission")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot contain app mappings", result.stderr)


class PreparationTests(Project):
    def test_archives_are_deterministic_and_checksums_match(self):
        first = prepare_release.prepare(self.output, root=self.root)
        second = prepare_release.prepare(self.base / "second", root=self.root)
        self.assertEqual(first["artifacts"], second["artifacts"])
        for name, digest in first["artifacts"].items():
            self.assertEqual(
                hashlib.sha256((self.output / name).read_bytes()).hexdigest(), digest
            )
        self.assertEqual(first["sourceCommit"], self.git("rev-parse", "HEAD"))
        self.assertFalse(first["sourceDirty"])
        self.assertEqual(first["openai"]["status"], "portal_upload_required")

    def test_wrong_tag_or_dirty_tagged_source_is_refused(self):
        with self.assertRaisesRegex(ValueError, "tag must match"):
            prepare_release.prepare(self.output, tag="v999.0.0", root=self.root)
        with (self.root / "README.md").open("a") as file:
            file.write("\nFixture uncommitted change\n")
        with self.assertRaisesRegex(ValueError, "Commit tracked changes"):
            prepare_release.prepare(self.output, tag=f"v{self.version}", root=self.root)
        self.assertFalse(self.output.exists())

    def test_failed_live_check_produces_no_release_artifacts(self):
        with patch(
            "prepare_release.check", side_effect=ValueError("Fixture discovery failed")
        ):
            with self.assertRaisesRegex(ValueError, "discovery failed"):
                prepare_release.prepare(self.output, check_live=True, root=self.root)
        self.assertFalse(self.output.exists())

    def test_offline_or_failed_repeat_invalidates_old_preflight(self):
        with patch("prepare_release.check", return_value=check_mcp.check(discovery)):
            first = prepare_release.prepare(
                self.output, check_live=True, root=self.root
            )
        self.assertTrue((self.output / "preflight.json").is_file())
        second = prepare_release.prepare(self.output, root=self.root)
        self.assertEqual(first, second)
        self.assertFalse((self.output / "preflight.json").exists())
        with patch("prepare_release.check", return_value=check_mcp.check(discovery)):
            prepare_release.prepare(self.output, check_live=True, root=self.root)
        with patch("prepare_release.check", side_effect=ValueError("Fixture failure")):
            with self.assertRaises(ValueError):
                prepare_release.prepare(self.output, check_live=True, root=self.root)
        self.assertFalse((self.output / "preflight.json").exists())


class AssetTests(Project):
    def setUp(self):
        super().setUp()
        prepare_release.prepare(self.output, root=self.root)
        self.remote = {}
        self.actions = []

    def fake_gh(self, *args):
        self.actions.append(args)
        if args[1] == "view":
            return json.dumps({"assets": [{"name": n} for n in self.remote]})
        if args[1] == "download":
            name, directory = (
                args[args.index("--pattern") + 1],
                args[args.index("--dir") + 1],
            )
            (Path(directory) / name).write_bytes(self.remote[name])
        elif args[1] == "upload":
            path = Path(args[3])
            self.assertNotIn(path.name, self.remote)
            self.remote[path.name] = path.read_bytes()
        else:
            self.fail("Unexpected GitHub command")
        return ""

    def test_attach_is_idempotent_without_overwriting_published_files(self):
        first = attach("v" + self.version, self.output, self.fake_gh)
        self.assertEqual(len(first["uploaded"]), 4)
        self.actions.clear()
        second = attach("v" + self.version, self.output, self.fake_gh)
        self.assertEqual(second["uploaded"], [])
        self.assertFalse(any(a[1] == "upload" for a in self.actions))

    def test_changed_published_file_blocks_all_uploads(self):
        self.remote["release.json"] = b"changed fixture"
        with self.assertRaisesRegex(ValueError, "Published release asset differs"):
            attach("v" + self.version, self.output, self.fake_gh)
        self.assertFalse(any(a[1] == "upload" for a in self.actions))

    def test_wrong_tag_or_local_archive_cannot_be_uploaded(self):
        with self.assertRaisesRegex(ValueError, "matching tag"):
            attach("v999.0.0", self.output, self.fake_gh)
        (self.output / f"wimbly-{self.version}.zip").write_bytes(b"changed fixture")
        with self.assertRaisesRegex(ValueError, "Local release archive checksum"):
            attach("v" + self.version, self.output, self.fake_gh)
        self.assertEqual(self.actions, [])


class PromotionTests(Project):
    def setUp(self):
        super().setUp()
        self.origin = self.base / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", str(self.origin)], check=True, capture_output=True
        )
        self.git("remote", "add", "origin", str(self.origin))
        self.git("push", "origin", "main")
        self.tag_and_prepare()

    def tag_and_prepare(self):
        self.version = json.loads((self.root / "plugin.json").read_text())["version"]
        self.git("tag", "v" + self.version)
        self.git("push", "origin", "v" + self.version)
        self.source = self.git("rev-parse", "HEAD")
        self.event = {
            "action": "released",
            "repository": {"full_name": REPOSITORY},
            "release": {
                "tag_name": "v" + self.version,
                "draft": False,
                "prerelease": False,
            },
        }
        with patch("prepare_release.check", return_value=check_mcp.check(discovery)):
            prepare_release.prepare(self.output, check_live=True, root=self.root)

    def apply(self, event=None, apply=True):
        return promote(
            event or self.event, self.source, self.output, apply=apply, root=self.root
        )

    def remote_branch(self):
        return self.git("ls-remote", "--heads", "origin", "refs/heads/" + BRANCH)

    def change_version(self, version):
        for name in ("plugin.json", ".claude-plugin/plugin.json"):
            path = self.root / name
            manifest = json.loads(path.read_text())
            manifest["version"] = version
            path.write_text(json.dumps(manifest, indent=2) + "\n")
        self.git("add", ".")
        self.git("commit", "-m", "Fixture version " + version)
        self.git("push", "origin", "main")
        self.tag_and_prepare()

    def test_dry_run_does_not_create_a_remote_branch(self):
        self.assertEqual(self.apply(apply=False)["status"], "dry_run")
        self.assertEqual(self.remote_branch(), "")

    def test_real_local_push_is_exact_and_repeat_is_idempotent(self):
        self.assertEqual(self.apply()["status"], "promoted_for_claude_scan")
        self.assertTrue(self.remote_branch().startswith(self.source + "\t"))
        self.assertEqual(self.apply()["status"], "already_promoted")

    def test_prerelease_draft_wrong_repository_or_wrong_event_cannot_promote(self):
        invalid = [
            {"release": {**self.event["release"], "prerelease": True}},
            {"release": {**self.event["release"], "draft": True}},
            {"repository": {"full_name": "other/repository"}},
            {"action": "published"},
        ]
        for change in invalid:
            with self.subTest(change=change):
                event = copy.deepcopy(self.event)
                event.update(change)
                with self.assertRaises(ValueError):
                    self.apply(event)
                self.assertEqual(self.remote_branch(), "")

    def test_unmatched_source_or_changed_archive_cannot_promote(self):
        with self.assertRaisesRegex(ValueError, "must agree"):
            promote(self.event, "a" * 40, self.output, apply=True, root=self.root)
        archive = self.output / f"wimbly-{self.version}-openai-submission.zip"
        archive.write_bytes(archive.read_bytes() + b"tampered fixture")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.apply()
        self.assertEqual(self.remote_branch(), "")

    def test_remotely_changed_tag_is_refused(self):
        original = self.source
        with (self.root / "README.md").open("a") as file:
            file.write("\nFixture moved tag\n")
        self.git("add", ".")
        self.git("commit", "-m", "Fixture remote tag replacement")
        replacement = self.git("rev-parse", "HEAD")
        self.git("push", "origin", "main")
        subprocess.run(
            [
                "git",
                "--git-dir",
                str(self.origin),
                "update-ref",
                "refs/tags/v" + self.version,
                replacement,
            ],
            check=True,
        )
        self.git("checkout", "--detach", original)
        with self.assertRaisesRegex(ValueError, "remote release tag changed"):
            self.apply()
        self.assertEqual(self.remote_branch(), "")

    def test_preflight_is_required(self):
        path = self.output / "preflight.json"
        data = json.loads(path.read_text())
        data["checks"] = []
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "passing public preflight"):
            self.apply()
        self.assertEqual(self.remote_branch(), "")

    def test_stale_preflight_is_refused(self):
        path = self.output / "preflight.json"
        data = json.loads(path.read_text())
        data["createdAt"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "fresh passing public preflight"):
            self.apply()
        self.assertEqual(self.remote_branch(), "")

    def test_new_release_advances_and_old_event_cannot_roll_back(self):
        self.apply()
        old_source, old_event = self.source, self.event
        self.change_version("99.0.0")
        self.apply()
        newest = self.source
        self.git("checkout", "--detach", old_source)
        with patch("prepare_release.check", return_value=check_mcp.check(discovery)):
            prepare_release.prepare(self.output, check_live=True, root=self.root)
        with self.assertRaisesRegex(ValueError, "cannot move backwards"):
            promote(old_event, old_source, self.output, apply=True, root=self.root)
        self.assertTrue(self.remote_branch().startswith(newest + "\t"))

    def test_descendant_commit_cannot_reduce_version(self):
        self.apply()
        previous = self.source
        self.change_version("0.0.0")
        with self.assertRaisesRegex(ValueError, "increase the plugin version"):
            self.apply()
        self.assertTrue(self.remote_branch().startswith(previous + "\t"))

    def test_unmerged_commit_cannot_promote(self):
        self.git("checkout", "-b", "unmerged-fixture")
        with (self.root / "README.md").open("a") as file:
            file.write("\nUnmerged fixture\n")
        self.git("add", ".")
        self.git("commit", "-m", "Unmerged fixture")
        self.source = self.git("rev-parse", "HEAD")
        self.git("tag", "-f", "v" + self.version)
        self.git("push", "--force", "origin", "v" + self.version)
        with patch("prepare_release.check", return_value=check_mcp.check(discovery)):
            prepare_release.prepare(self.output, check_live=True, root=self.root)
        with self.assertRaisesRegex(ValueError, "already belong to main"):
            self.apply()
        self.assertEqual(self.remote_branch(), "")

    def test_stable_version_validation(self):
        for invalid in ("1.0.0-rc.1", "01.0.0", "1.2", "1.2.3+build"):
            with self.subTest(version=invalid), self.assertRaises(ValueError):
                stable_version(invalid)


if __name__ == "__main__":
    unittest.main()
