#!/usr/bin/env python3
"""Outbound disclosure check for the public Souls of Muse repository.

Scans tracked text files (and optionally commit messages) for material that
must not leave the private working environment: credentials, personal home
paths, private network addresses, personal e-mail addresses and phone
numbers, links into private workspaces, internal tracker identifiers and
link-only shares. See docs/DISCLOSURE_POLICY.md.

A private denylist of internal names (machines, people, partners, internal
projects) is read from the DISCLOSURE_DENYLIST environment variable and/or
the git-ignored file private/disclosure-denylist.txt. One literal term per
line, case-insensitive, '#' starts a comment. Denylist terms are never
printed; findings refer to them by number only, so CI logs stay clean.

Standard library only. Exit status: 0 clean, 1 findings, 2 usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DENYLIST_FILE = ROOT / "private" / "disclosure-denylist.txt"
SUPPRESS_MARK = "disclosure: allow"
PLACEHOLDER = re.compile(r"<!-- FILL(?::[^>]*)? -->")
MAX_BYTES = 5 * 1024 * 1024

# Placeholder secrets used by offline tests are allowed only when they say so.
FAKE_VALUE = re.compile(r"(fake|dummy|example|placeholder|not[-_ ]a[-_ ]real|redacted|xxxx|<[^>]+>)", re.I)

ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]{2,}")

ALLOWED_EMAIL = re.compile(
    r"(@users\.noreply\.github\.com$|^noreply@|^no-reply@|@example\.(com|org|net)$|@anthropic\.com$)", re.I
)


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern
    secret: bool = False  # mask the match in output


RULES = [
    # Credentials
    Rule("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), True),
    Rule("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), True),
    Rule("github-token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}"), True),
    Rule("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), True),
    Rule("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), True),
    Rule("openai-style-key", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}"), True),
    Rule("bearer-token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{24,}"), True),
    Rule("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), True),
    Rule(
        "assigned-secret",
        re.compile(
            r"(?i)\b[A-Z0-9_]*(?:api[_-]?key|secret|token|passw(?:or)?d)[A-Z0-9_]*['\"]?\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]"
        ),
        True,
    ),
    # Personal machine paths
    Rule("home-path", re.compile(r"/Users/[A-Za-z0-9._-]+|/home/(?!user/|runner/|username\b)[a-z][a-z0-9._-]+/|[A-Za-z]:\\\\?Users\\\\?[A-Za-z0-9._-]+")),
    Rule("local-file-url", re.compile(r"\bfile://|\bobsidian://")),
    # Private network addresses (RFC1918, CGNAT/overlay VPN, link-local)
    Rule(
        "private-ip",
        re.compile(
            r"(?<![\d.])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
            r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}|169\.254\.\d{1,3}\.\d{1,3})(?![\d.])"
        ),
    ),
    Rule("vpn-hostname", re.compile(r"(?i)\b[a-z0-9-]+\.(?:ts\.net|tailscale\.net|zerotier\.com|local)\b")),
    # Private workspaces and link-only shares
    Rule(
        "private-workspace-link",
        re.compile(
            r"(?i)\b(?:linear\.app/|discord(?:app)?\.com/channels/|[a-z0-9-]+\.slack\.com/|[a-z0-9-]+\.notion\.site/|notion\.so/"
            r"|docs\.google\.com/|drive\.google\.com/|[a-z0-9-]+\.kimi\.page|claude\.ai/(?:code/)?(?:artifact|chat|share)"
            r"|chatgpt\.com/(?:share|c)/|[a-z0-9-]+\.trycloudflare\.com|[a-z0-9-]+\.ngrok(?:-free)?\.(?:io|app|dev)"
            r"|uploads\.linear\.app|[a-z0-9-]+-[a-z0-9]+\.vercel\.app)"
        ),
    ),
    # Internal tracker identifiers
    Rule("internal-tracker-id", re.compile(r"\bAI3-\d+\b")),
    # Personal contact data
    Rule("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    Rule("phone", re.compile(r"(?<![\w.])\+\d{1,3}[\s()-]*\d{2,4}[\s()-]*\d{3}[\s-]*\d{2}[\s-]*\d{2,4}(?![\w.])")),
]

SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".mp4", ".mov", ".webm", ".mp3", ".wav", ".ogg",
    ".woff", ".woff2", ".ttf", ".otf", ".zip", ".gz", ".tar", ".ots", ".sqlite", ".sqlite3", ".db",
}


@dataclass(frozen=True)
class Finding:
    where: str
    line: int
    rule: str
    excerpt: str
    severity: str = "error"

    def render(self) -> str:
        return f"{self.where}:{self.line}: {self.severity}: {self.rule}: {self.excerpt}"


def load_denylist(env: dict | None = None) -> list[str]:
    env = os.environ if env is None else env
    raw = env.get("DISCLOSURE_DENYLIST", "")
    if DENYLIST_FILE.is_file():
        raw += "\n" + DENYLIST_FILE.read_text(encoding="utf-8")
    terms = []
    for line in raw.splitlines():
        term = line.split("#", 1)[0].strip()
        if term and term.lower() not in (t.lower() for t in terms):
            terms.append(term)
    return terms


def compile_denylist(terms: list[str]) -> list[re.Pattern]:
    # Word-ish boundaries that also work for non-ASCII terms.
    return [re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w])", re.I) for t in terms]


def mask(text: str) -> str:
    if len(text) <= 8:
        return "*" * len(text)
    return text[:4] + "…" + f"[{len(text)} chars masked]"


def _allowed(rule: Rule, match: re.Match) -> bool:
    value = match.group(0)
    if rule.name == "email":
        return bool(ALLOWED_EMAIL.search(value))
    if rule.name == "assigned-secret":
        value = match.group(1)
        # An environment-variable *name* is configuration, not a secret.
        return bool(FAKE_VALUE.search(value) or ENV_NAME.fullmatch(value))
    if rule.name in {"openai-style-key", "bearer-token"}:
        return bool(FAKE_VALUE.search(value))
    return False


def scan_text(text: str, where: str, deny: list[re.Pattern], release: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if PLACEHOLDER.search(line):
            findings.append(Finding(where, lineno, "unfilled-placeholder", line.strip()[:80], "error" if release else "warning"))
        if SUPPRESS_MARK in line:
            continue
        for rule in RULES:
            for m in rule.pattern.finditer(line):
                if _allowed(rule, m):
                    continue
                shown = mask(m.group(0)) if rule.secret else m.group(0)[:120]
                findings.append(Finding(where, lineno, rule.name, shown))
        for idx, pat in enumerate(deny, 1):
            if pat.search(line):
                findings.append(Finding(where, lineno, "private-denylist", f"term #{idx} (value not printed)"))
    return findings


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [ROOT / p for p in out.decode("utf-8").split("\0") if p]


def scan_file(path: Path, deny: list[re.Pattern], release: bool) -> list[Finding]:
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
        return []
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        return [Finding(rel, 0, "file-too-large-to-scan", f"{len(data)} bytes; review manually")]
    if b"\0" in data[:8192]:
        return []
    return scan_text(data.decode("utf-8", errors="replace"), rel, deny, release)


def scan_commits(rev_range: str, deny: list[re.Pattern]) -> list[Finding]:
    fmt = "%H%x00%an <%ae>%x00%cn <%ce>%x00%B%x1e"
    proc = subprocess.run(["git", "log", f"--format={fmt}", rev_range], cwd=ROOT, capture_output=True)
    if proc.returncode != 0:
        print(f"disclosure-check: cannot read commits {rev_range!r}: {proc.stderr.decode().strip()}", file=sys.stderr)
        raise SystemExit(2)
    out = proc.stdout.decode("utf-8", errors="replace")
    findings: list[Finding] = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, author, committer, body = (record.split("\0") + ["", "", ""])[:4]
        where = f"commit {sha[:12]}"
        findings += scan_text(f"{author}\n{committer}\n{body}", where, deny)
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", help="files to scan (default: all git-tracked files)")
    ap.add_argument("--commits", metavar="RANGE", help="also scan commit metadata and messages, e.g. origin/main..HEAD")
    ap.add_argument("--release", action="store_true", help="treat unfilled FILL placeholders as errors (use before submission)")
    args = ap.parse_args(argv)

    terms = load_denylist()
    deny = compile_denylist(terms)
    paths = [Path(p).resolve() for p in args.paths] if args.paths else tracked_files()

    findings: list[Finding] = []
    for path in paths:
        findings += scan_file(path, deny, args.release)
    if args.commits:
        findings += scan_commits(args.commits, deny)

    errors = [f for f in findings if f.severity == "error"]
    for f in findings:
        print(f.render())
    print(
        f"disclosure-check: {len(paths)} files, {len(terms)} private denylist terms, "
        f"{len(errors)} errors, {len(findings) - len(errors)} warnings",
        file=sys.stderr,
    )
    if not terms:
        print("disclosure-check: note: no private denylist loaded; internal names are not checked", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
