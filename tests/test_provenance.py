import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.provenance_manifest import (
    build_manifest,
    canonical_json,
    safe_artifact_path,
    safe_download_url,
    sha256_of_file,
)

COMMIT = "a" * 40
REPO = "owner/repo"
ARCH = "b" * 64
ROOT = Path(__file__).resolve().parents[1]


class ManifestTest(unittest.TestCase):
    def test_deterministic_canonical_json(self):
        m1 = build_manifest(COMMIT, REPO, ARCH, "snapshot-abc.tar.gz", "2026-01-01T00:00:00Z")
        m2 = build_manifest(COMMIT, REPO, ARCH, "snapshot-abc.tar.gz", "2026-01-01T00:00:00Z")
        self.assertEqual(canonical_json(m1), canonical_json(m2))
        self.assertIn("pending", canonical_json(m1))
        self.assertFalse(m1["claims"]["identity_assertion"])
        self.assertEqual(m1["archive_sha256"], ARCH)
        self.assertEqual(m1["hash_algorithm"], "SHA256")

    def test_manifest_records_content_hash(self):
        d = tempfile.mkdtemp(prefix="cx1-provenance-")
        p = os.path.join(d, "sample.bin")
        with open(p, "wb") as f:
            f.write(b"hello")
        digest = sha256_of_file(p)
        m = build_manifest(COMMIT, REPO, digest, "snapshot-abc.tar.gz", "2026-01-01T00:00:00Z")
        self.assertEqual(json.loads(canonical_json(m))["archive_sha256"], digest)

    def test_reject_unsafe_artifact_paths(self):
        for bad in ["../evil", "a/b", "", ".ots", "x\\y", "has space"]:
            with self.assertRaises(ValueError):
                safe_artifact_path(bad)
        self.assertEqual(safe_artifact_path("manifest-abc123.json"), "manifest-abc123.json")

    def test_reject_unsafe_download_urls(self):
        good = "https://github.com/owner/repo/releases/download/evidence-abc/manifest.json"
        self.assertEqual(safe_download_url(good), good)
        for bad in [
            "http://github.com/owner/repo/x",
            "https://evil.example.com/x.ots",
            "https://github.com/owner/repo/x y",
        ]:
            with self.assertRaises(ValueError):
                safe_download_url(bad)

    def test_ots_target_is_manifest_not_archive(self):
        m = build_manifest(COMMIT, REPO, ARCH, "snapshot-aaaaaaaaaaaa.tar.gz", "2026-01-01T00:00:00Z")
        self.assertEqual(m["ots_target"], "manifest-aaaaaaaaaaaa.json")
        self.assertNotEqual(m["ots_target"], m["archive_name"])
        m2 = build_manifest(COMMIT, REPO, ARCH, "snapshot-x.tar.gz", "2026-01-01T00:00:00Z", manifest_name="manifest-custom.json")
        self.assertEqual(m2["ots_target"], "manifest-custom.json")

    def test_claims_prepared_and_commit_date_not_proven(self):
        m = build_manifest(COMMIT, REPO, ARCH, "snapshot-abc.tar.gz", "2026-01-01T00:00:00Z")
        self.assertEqual(m["claims"]["status"], "prepared")
        self.assertEqual(m["created_utc"], "2026-01-01T00:00:00Z")
        self.assertEqual(m["commit_date_utc_claimed"], "2026-01-01T00:00:00Z")
        self.assertFalse(m["commit_date_proven"])
        self.assertIn("not a proven timestamp", m["claims"]["note"])
        self.assertIn("untrusted", m["created_utc_basis"])

    def test_canonical_manifest_consistent(self):
        m = build_manifest(COMMIT, REPO, ARCH, "snapshot-abc.tar.gz", "2026-01-01T00:00:00Z")
        text = canonical_json(m)
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(json.loads(text), m)
        self.assertEqual(text, canonical_json(json.loads(text)))

    def test_reject_invalid_created_utc(self):
        for bad in ["", "2026-13-01T00:00:00Z", "2026-02-30T00:00:00Z", "2026-01-01 00:00:00", "2026-01-01T00:00:00+00:00", "2026-01-01", "not-a-date"]:
            with self.assertRaises(ValueError):
                build_manifest(COMMIT, REPO, ARCH, "snapshot-abc.tar.gz", bad)

    def test_reject_non_40_char_commit(self):
        for bad in ["a" * 64, "a" * 39, "A" * 40, "g" * 40]:
            with self.assertRaises(ValueError):
                build_manifest(bad, REPO, ARCH, "snapshot-abc.tar.gz", "2026-01-01T00:00:00Z")

    def test_cli_rejects_invalid_utc_and_output_path(self):
        base = [sys.executable, "scripts/provenance_manifest.py", "--commit", COMMIT, "--repo", REPO, "--archive-sha", ARCH, "--archive-name", "snapshot-abc.tar.gz"]
        r = subprocess.run(base + ["--created-utc", "2026-13-01T00:00:00Z", "--out", "manifest-x.json"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        for out in ["../evil.json", "sub/manifest-x.json", "/tmp/manifest-x.json"]:
            r = subprocess.run(base + ["--created-utc", "2026-01-01T00:00:00Z", "--out", out], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, out)


if __name__ == "__main__":
    unittest.main()
