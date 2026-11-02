from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
SPEC = spec_from_file_location("jdbc_history", ROOT / "scripts/ci/verify_jdbc_history_fixture.py")
assert SPEC and SPEC.loader
VERIFIER = module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def original_fixture() -> bytes:
    # Frozen immutable source; keep the noncredential URI in explicit test parts.
    source = (ROOT / "tests/fixtures/keycloak-history-source.txt").read_text()
    public_uri = "jdbc:postgresql://" + "keycloak-db:5432/" + "keycloak"
    return source.replace("CI_DATABASE_URI_PLACEHOLDER", public_uri).encode()


def test_exact_original_source_and_reviewed_fingerprint_set():
    VERIFIER.validate_fixture(original_fixture())
    VERIFIER.validate_fingerprints((ROOT / ".gitleaksignore").read_text())


@pytest.mark.parametrize("mutation", ["line", "other_line", "missing", "shift"])
def test_rewritten_or_missing_immutable_object_is_rejected(mutation):
    source = original_fixture()
    if mutation == "line":
        source = source.replace(b":5432/", b":5433/")
    elif mutation == "other_line":
        source += b"# different source\n"
    elif mutation == "missing":
        source = b""
    else:
        source = b"\n" + source
    with pytest.raises(ValueError):
        VERIFIER.validate_fixture(source)


@pytest.mark.parametrize("mutation", ["unknown", "duplicate", "missing"])
def test_unknown_duplicate_or_missing_history_exceptions_are_rejected(mutation):
    source = (ROOT / ".gitleaksignore").read_text()
    if mutation == "unknown":
        source += "unreviewed:fixture:generic-api-key:1\n"
    elif mutation == "duplicate":
        source += VERIFIER.FINGERPRINT + "\n"
    else:
        source = source.replace(VERIFIER.FINGERPRINT + "\n", "")
    with pytest.raises(ValueError):
        VERIFIER.validate_fingerprints(source)


def test_wrong_repository_is_rejected_before_git(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "other/telnexa")
    monkeypatch.setenv("GITHUB_REPOSITORY_ID", "1334764612")
    with patch.object(VERIFIER.subprocess, "run") as git:
        with pytest.raises(ValueError):
            VERIFIER.main()
        git.assert_not_called()


def test_unavailable_git_object_fails_closed(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "appolon1908/telnexa")
    monkeypatch.setenv("GITHUB_REPOSITORY_ID", "1334764612")
    with patch.object(
        VERIFIER.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "git")
    ):
        with pytest.raises(subprocess.CalledProcessError):
            VERIFIER.main()


def test_git_blob_binding_is_independently_enforced(monkeypatch):
    monkeypatch.setattr(VERIFIER, "BLOB_SHA1", "0" * 40)
    with pytest.raises(ValueError, match="Git blob"):
        VERIFIER.validate_fixture(original_fixture())


def test_line_binding_is_independently_enforced(monkeypatch):
    monkeypatch.setattr(VERIFIER, "LINE_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="line checksum"):
        VERIFIER.validate_fixture(original_fixture())


def test_wrong_repository_id_is_rejected_before_git(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "appolon1908/telnexa")
    monkeypatch.setenv("GITHUB_REPOSITORY_ID", "0")
    with patch.object(VERIFIER.subprocess, "run") as git:
        with pytest.raises(ValueError):
            VERIFIER.main()
        git.assert_not_called()


def test_immutable_object_fetch_does_not_narrow_history_or_change_refs(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "appolon1908/telnexa")
    monkeypatch.setenv("GITHUB_REPOSITORY_ID", "1334764612")
    results = [
        subprocess.CompletedProcess([], 0, stdout=b""),
        subprocess.CompletedProcess([], 0, stdout=original_fixture()),
    ]
    with patch.object(VERIFIER.subprocess, "run", side_effect=results) as git:
        VERIFIER.main()
    assert git.call_args_list[0].args[0] == [
        "git",
        "fetch",
        "--no-tags",
        "--no-write-fetch-head",
        "--no-recurse-submodules",
        "https://github.com/appolon1908/telnexa.git",
        VERIFIER.COMMIT,
    ]
    assert git.call_args_list[1].args[0] == [
        "git",
        "show",
        f"{VERIFIER.COMMIT}:{VERIFIER.SOURCE_PATH}",
    ]
    assert all(
        call.kwargs == {"check": True, "capture_output": True} for call in git.call_args_list
    )
