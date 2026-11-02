"""Execute the actual Docker account guards against temporary inherited files."""

from pathlib import Path
import subprocess

import pytest


DOCKERFILE = (Path(__file__).parents[1] / "docker/keycloak/Dockerfile").read_text()


def commands(tmp_path):
    start = DOCKERFILE.index("RUN set -eu;")
    end = DOCKERFILE.index("    rpm --root", start)
    capture = DOCKERFILE[start + 4 : end]
    start = DOCKERFILE.index("    && for account", DOCKERFILE.index("&& bash /tmp/curate"))
    end = DOCKERFILE.index("    && rpm --root", start)
    guard = "set -eu; : " + DOCKERFILE[start:end] + " && :"
    for old, new in (
        ("/mnt/rootfs", str(tmp_path / "rootfs")),
        ("/tmp/inherited-accounts", str(tmp_path / "captured")),
        ("/tmp/account.metadata", str(tmp_path / "metadata")),
    ):
        capture = capture.replace(old, new)
        guard = guard.replace(old, new)
    return capture.replace("\\\n", " "), guard.replace("\\\n", " ")


@pytest.mark.parametrize(
    "mutation", ["unchanged", "bytes", "mode", "missing", "new_file", "symlink"]
)
def test_actual_inherited_account_guard_fails_closed(tmp_path, mutation):
    etc = tmp_path / "rootfs/etc"
    etc.mkdir(parents=True)
    for name in ("passwd", "group", "shadow"):
        path = etc / name
        path.write_text("isolated immutable account fixture\n")
        path.chmod(0o640)
    capture, guard = commands(tmp_path)
    subprocess.run(["bash", "-c", capture], check=True)
    if mutation == "bytes":
        (etc / "passwd").write_text("modified account fixture\n")
    elif mutation == "mode":
        (etc / "group").chmod(0o644)
    elif mutation == "missing":
        (etc / "shadow").unlink()
    elif mutation == "new_file":
        (etc / "gshadow").write_text("unreviewed account file\n")
    elif mutation == "symlink":
        (etc / "passwd").unlink()
        (etc / "passwd").symlink_to(etc / "group")
    result = subprocess.run(["bash", "-c", guard], capture_output=True)
    assert (result.returncode == 0) is (mutation == "unchanged")
