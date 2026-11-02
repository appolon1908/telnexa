"""Verify one reviewed immutable, credential-free CI fixture before history scans."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess


COMMIT = "152585aa5525f1182d56ed939ac0729c9095d12f"
SOURCE_PATH = "scripts/ci/keycloak-candidate-compatibility.sh"
BLOB_SHA1 = "8af45c307ac9055b2e72293c6f1e8ccd20ea4640"
SOURCE_SHA256 = "e54e6ee9df9d320512148deec8ef754749cd3c5deae3c958afa83592bc1b5f3b"
LINE_SHA256 = "1a9fcd6b9e27e95ad44f478144557f7fbd65fb7b4c6b193461365081d6055db4"
FINGERPRINT = f"{COMMIT}:{SOURCE_PATH}:generic-api-key:35"
EXISTING_FINGERPRINTS = {
    "515b29481dd638f227eadc611c0a7dc2b92acbdd:.github/workflows/step4-format-artifact.yml:generic-api-key:28",
    "67ec59e447bb73334f1edb7042e937977cf2ec8e:labs/middleware_telnexa/certify.py:generic-api-key:72",
    "4b4e5c73463df1c03723438d97bffd9b73393b95:docker-compose.yml:generic-api-key:45",
    "ed555db547bf161123ee6a3277a4262c3c6005e7:DEPLOYMENT_REPORT.md:generic-api-key:54",
}


def validate_fixture(source: bytes) -> None:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError("immutable source checksum mismatch")
    blob = b"blob " + str(len(source)).encode("ascii") + b"\0" + source
    if hashlib.sha1(blob).hexdigest() != BLOB_SHA1:
        raise ValueError("immutable Git blob mismatch")
    lines = source.splitlines()
    if len(lines) < 35 or hashlib.sha256(lines[34]).hexdigest() != LINE_SHA256:
        raise ValueError("immutable line checksum mismatch")


def validate_fingerprints(source: str) -> None:
    lines = source.splitlines()
    if len(lines) != 5 or set(lines) != EXISTING_FINGERPRINTS | {FINGERPRINT}:
        raise ValueError("unreviewed or duplicate history exception")


def main() -> None:
    if (os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_REPOSITORY_ID")) != (
        "appolon1908/telnexa",
        "1334764612",
    ):
        raise ValueError("unreviewed repository identity")
    # Squash merges need not retain the PR commit in main's ancestry. Fetch
    # only its immutable reviewed object without changing HEAD, refs, FETCH_HEAD
    # or shallow boundaries; scan ancestry and source identity remain unchanged.
    subprocess.run(
        [
            "git",
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            "--no-recurse-submodules",
            "https://github.com/appolon1908/telnexa.git",
            COMMIT,
        ],
        check=True,
        capture_output=True,
    )
    source = subprocess.run(
        ["git", "show", f"{COMMIT}:{SOURCE_PATH}"], check=True, capture_output=True
    ).stdout
    validate_fixture(source)
    validate_fingerprints(Path(".gitleaksignore").read_text())
    print("Exact immutable credential-free historical CI fixture verified")


if __name__ == "__main__":
    main()
