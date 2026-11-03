import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import disclosure_check as dc

ROOT = Path(__file__).resolve().parents[1]

# Test inputs are assembled from pieces so that this file itself never contains
# a contiguous token or address that the scanner (or any other scanner) flags.
HOME = "/" + "Users" + "/someone/Projects/notes.md"
PRIV_IP = "192." + "168.1.20"
CGNAT_IP = "100." + "101.2.3"
GH_TOKEN = "gh" + "p_" + "A" * 36
EMAIL = "person" + "@" + "mail.example-corp.kz"
TRACKER = "AI3" + "-123"
LINK_SHARE = "https://abc123" + ".kimi." + "page/"
PRIVATE_LINK = "https://linear" + ".app/team/issue/X-1"


def rules(text, deny=(), release=False):
    return [f.rule for f in dc.scan_text(text, "t", dc.compile_denylist(list(deny)), release) if f.severity == "error"]


class RuleTest(unittest.TestCase):
    def test_clean_text_passes(self):
        self.assertEqual(rules("Muse Spark reviews the terminology table.\nSee docs/DISCLOSURE_POLICY.md"), [])

    def test_home_path(self):
        self.assertIn("home-path", rules(f"saved to {HOME}"))
        self.assertEqual(rules("/home/user/souls-of-muse and /path/on/persistent/vm/lessons.db"), [])

    def test_private_and_overlay_ip(self):
        self.assertIn("private-ip", rules(f"ssh {PRIV_IP}"))
        self.assertIn("private-ip", rules(f"node at {CGNAT_IP}"))
        self.assertEqual(rules("version 2.1.317 and 8.8.8.8"), [])

    def test_token_is_detected_and_masked(self):
        findings = dc.scan_text(f"token {GH_TOKEN}", "t", [])
        self.assertEqual([f.rule for f in findings], ["github-token"])
        self.assertNotIn(GH_TOKEN, findings[0].render())

    def test_assigned_secret_allows_fakes_and_env_names(self):
        self.assertIn("assigned-secret", rules('API_KEY = "' + "q7Rk2LmZ9xPw" + '"'))
        self.assertEqual(rules('{"MODEL_API_KEY": "cx1-fake-key-not-a-real-secret"}'), [])
        self.assertEqual(rules("api_key_env: 'MODEL_API_KEY'"), [])

    def test_email_allows_noreply(self):
        self.assertIn("email", rules(f"write to {EMAIL}"))
        self.assertEqual(rules("1+user@users.noreply.github.com and noreply@anthropic.com"), [])

    def test_private_workspace_and_link_shares(self):
        self.assertIn("private-workspace-link", rules(f"see {PRIVATE_LINK}"))
        self.assertIn("private-workspace-link", rules(f"dashboard {LINK_SHARE}"))
        self.assertEqual(rules("https://preview.soulsofmuse.com/ and https://github.com/x/y"), [])

    def test_tracker_id(self):
        self.assertIn("internal-tracker-id", rules(f"done in {TRACKER}"))

    def test_suppression_marker(self):
        self.assertEqual(rules(f"example {PRIV_IP}  <!-- disclosure: allow private-ip -->"), [])

    def test_placeholder_is_warning_until_release(self):
        text = "<!-- " + "FILL: evidence link -->"
        self.assertEqual(rules(text), [])
        self.assertEqual(rules(text, release=True), ["unfilled-placeholder"])


class DenylistTest(unittest.TestCase):
    def test_terms_matched_case_insensitive_and_never_printed(self):
        secret_name = "Zebra" + "Node7"
        findings = dc.scan_text(f"runs on zebranode7 tonight", "t", dc.compile_denylist([secret_name]))
        self.assertEqual([f.rule for f in findings], ["private-denylist"])
        self.assertNotIn(secret_name.lower(), findings[0].render().lower())

    def test_word_boundary(self):
        self.assertEqual(rules("XQZ9 parser", deny=["QZ9"]), [])
        self.assertEqual(rules("on QZ9 today", deny=["QZ9"]), ["private-denylist"])
        self.assertEqual(rules("на Ромашкине", deny=["Ромашкин"]), [])
        self.assertEqual(rules("в Ромашкин ушло", deny=["Ромашкин"]), ["private-denylist"])

    def test_env_and_comments(self):
        terms = dc.load_denylist({"DISCLOSURE_DENYLIST": "Alpha  # machine\n\n# note\nbeta\nALPHA"})
        self.assertEqual([t.lower() for t in terms if t.lower() in {"alpha", "beta"}], ["alpha", "beta"])


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"DISCLOSURE_DENYLIST": ""}), redirect_stdout(out), redirect_stderr(err):
            code = dc.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_dirty_file_fails_and_binary_is_skipped(self):
        tmp = Path(tempfile.mkdtemp(prefix="disclosure-"))
        dirty = tmp / "note.md"
        dirty.write_text(f"path {HOME}\n", encoding="utf-8")
        binary = tmp / "blob.bin"
        binary.write_bytes(b"\0\1\2" + HOME.encode())
        code, out, _ = self.run_cli(str(dirty), str(binary))
        self.assertEqual(code, 1)
        self.assertIn("home-path", out)
        self.assertNotIn("blob.bin", out)

    def test_repository_is_clean(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 0, out + err)

    def test_script_runs_standalone(self):
        proc = subprocess.run(
            [sys.executable, "-I", str(ROOT / "scripts" / "disclosure_check.py"), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
