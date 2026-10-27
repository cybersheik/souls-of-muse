"""Build a canonical hash manifest for OpenTimestamps evidence. Stdlib only."""
import argparse
import hashlib
import json
import re
from datetime import datetime

SCHEMA = "souls-of-muse/provenance-manifest-v1"
FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ALLOWED_URL_PREFIXES = (
    "https://github.com/",
    "https://objects.githubusercontent.com/",
)


def safe_artifact_path(name: str) -> str:
    if not name or not FILENAME_RE.match(name):
        raise ValueError(f"unsafe artifact name: {name!r}")
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError(f"unsafe artifact name: {name!r}")
    return name


def safe_download_url(url: str) -> str:
    if not url.startswith(ALLOWED_URL_PREFIXES):
        raise ValueError(f"unsafe download url: {url!r}")
    if " " in url or "\\" in url:
        raise ValueError(f"unsafe download url: {url!r}")
    return url


def validate_created_utc(value: str) -> str:
    if not value or not UTC_RE.match(value):
        raise ValueError("created_utc must be YYYY-MM-DDTHH:MM:SSZ (git commit date, UTC)")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(f"invalid created_utc: {value!r}") from exc
    return value


def _derive_manifest_name(commit: str, archive_name: str) -> str:
    if archive_name.startswith("snapshot-") and archive_name.endswith(".tar.gz"):
        middle = archive_name[len("snapshot-"):-len(".tar.gz")]
        if middle and FILENAME_RE.match(middle):
            return safe_artifact_path(f"manifest-{middle}.json")
    return safe_artifact_path(f"manifest-{commit[:12]}.json")


def build_manifest(commit, repo, archive_sha256, archive_name, created_utc="", manifest_name=""):
    if not COMMIT_RE.match(commit or ""):
        raise ValueError("commit must be a 40-char lowercase hex SHA")
    if not REPO_RE.match(repo or ""):
        raise ValueError("repo must be owner/name")
    if not SHA256_RE.match(archive_sha256 or ""):
        raise ValueError("archive_sha256 must be sha256 hex")
    safe_artifact_path(archive_name)
    created = validate_created_utc(created_utc)
    ots_target = safe_artifact_path(manifest_name) if manifest_name else _derive_manifest_name(commit, archive_name)
    return {
        "schema": SCHEMA,
        "repo": repo,
        "commit_sha": commit,
        "archive_name": archive_name,
        "archive_sha256": archive_sha256,
        "hash_algorithm": "SHA256",
        "created_utc": created,
        "commit_date_utc_claimed": created,
        "commit_date_proven": False,
        "created_utc_basis": "git_commit_date_claimed_untrusted_not_proven_timestamp",
        "ots_target": ots_target,
        "claims": {
            "status": "prepared",
            "identity_assertion": False,
            "note": "Prepared before OpenTimestamps submission; calendar receipt, Bitcoin anchoring pending. Claimed commit date is not a proven timestamp.",
        },
    }


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--commit", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--archive-sha", required=True)
    p.add_argument("--archive-name", required=True)
    p.add_argument("--manifest-name", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--created-utc", default="")
    a = p.parse_args()
    try:
        if a.out != safe_artifact_path(a.out):
            raise ValueError("--out must be a safe basename only")
        safe_artifact_path(a.out)
        data = build_manifest(a.commit, a.repo, a.archive_sha, a.archive_name, a.created_utc, a.manifest_name)
    except ValueError as exc:
        p.error(str(exc))
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(canonical_json(data))


if __name__ == "__main__":
    main()
