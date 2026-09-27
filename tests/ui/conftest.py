"""Shared pytest configuration for Playwright UI tests.

Everything here exists so the UI suite is self-contained: it starts its own
NossiNet servers against temporary databases and temporary wikis, so no test
reads or writes the developer's real ``NN.db`` or ``~/wiki``.

Three things are centralised because duplicating them caused real bugs:

* ``browser_context_args`` — the servers use a self-signed certificate, so every
  test must ignore HTTPS errors. A module-level fixture of the same name silently
  shadows this one, which is how the flag got dropped from ``test_chat_timestamps``
  and broke it.

* ``nossi_server`` — one guarded way to start a server. It refuses to start if the
  port is taken, because otherwise the "is it up yet" check succeeds against a
  *stale* server from an abandoned run and every test quietly asserts against the
  wrong wiki or database.

* ``editor_wiki_server`` / ``app_server`` — servers with throwaway wikis, so tests
  that save a page cannot clobber ``~/wiki``.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
LIVE_DATABASE = REPO_ROOT / "NN.db"

# Port map. 5000 is the developer's own dev server and is never used by the suite.
# Each server needs its own port: they are session-scoped and coexist.
PORT_CHAT = 5001
PORT_SHEET = 5002
PORT_WIKI = 5003
PORT_APP = 5004


@pytest.fixture(scope="function")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Accept the local NossiNet servers' self-signed certificate."""
    return {**browser_context_args, "ignore_https_errors": True}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _port_is_open(port: int) -> bool:
    """Report whether something is already accepting connections on ``port``.

    Args:
        port: TCP port to probe.

    Returns:
        True if the port is reachable, False if it is free or filtered.
    """
    with socket.socket() as probe:
        probe.settimeout(0.5)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port(port: int, timeout: float) -> bool:
    """Block until something accepts connections on ``port``.

    Args:
        port: TCP port to poll.
        timeout: Seconds to keep trying before giving up.

    Returns:
        True if the port became reachable, False on timeout.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_is_open(port):
            return True
        time.sleep(0.25)
    return False


def _git(*args: str, cwd: Path) -> None:
    """Run a git command in ``cwd``, raising with output if it fails.

    Args:
        *args: Arguments to pass to git.
        cwd: Directory to run the command in.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed in {cwd}:\n{result.stdout}{result.stderr}"
        raise RuntimeError(msg)


def make_wiki(root: Path, pages: dict[str, Path]) -> Path:
    """Build a throwaway wiki root containing ``pages``, initialised as a git repo.

    The wiki must be a git repository with at least one commit: saving a page goes
    through ``WikiPage.save_overwrite`` -> ``commit_and_push``, which opens the wiki
    root as a repo and reads the latest commit.

    Args:
        root: Directory to populate. Created if missing.
        pages: Mapping of destination filename to source file to copy in.

    Returns:
        The wiki root path.
    """
    root.mkdir(parents=True, exist_ok=True)
    for name, source in pages.items():
        shutil.copy(source, root / name)

    _git("init", "-q", "-b", "main", ".", cwd=root)
    _git("config", "user.email", "nossitest@example.invalid", cwd=root)
    _git("config", "user.name", "NossiTest", cwd=root)
    _git("add", ".", cwd=root)
    _git("commit", "-q", "-m", "fixture wiki", cwd=root)
    return root


def make_database(source: Path) -> Path:
    """Copy a database next to the original so the suite may write to the copy.

    Args:
        source: Database to copy.

    Returns:
        Path to the writable copy.
    """
    target = source.parent / f"test_{source.name}"
    shutil.copy(source, target)
    return target


# --------------------------------------------------------------------------- #
# server factory
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def nossi_server() -> Iterator[Callable[..., str]]:
    """Provide a factory that starts NossiNet servers and tears them all down.

    Yields:
        Callable taking ``port`` plus optional ``database`` and ``wiki_root``
        keyword arguments, returning the server's base URL.
    """
    procs: list[subprocess.Popen[str]] = []

    def _start(
        port: int,
        *,
        database: Path | None = None,
        wiki_root: Path | None = None,
        startup_timeout: float = 30.0,
    ) -> str:
        if _port_is_open(port):
            msg = (
                f"Port {port} is already in use, so the test server cannot claim it. Another test "
                "server or a stale process from an abandoned run is holding it; free the port and retry."
            )
            pytest.fail(msg)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        if database is not None:
            env["DATABASE"] = str(database)
        if wiki_root is not None:
            env["NOSSI_WIKI_PATH"] = str(wiki_root)

        proc = subprocess.Popen(
            [sys.executable, "NossiNet.py", str(port)],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        procs.append(proc)

        if not _wait_for_port(port, timeout=startup_timeout):
            proc.terminate()
            output = proc.communicate(timeout=5)[0] or ""
            pytest.fail(f"Test server never came up on port {port}:\n{output}")

        return f"https://127.0.0.1:{port}"

    yield _start

    for proc in procs:
        if proc.poll() is not None:
            continue
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


# --------------------------------------------------------------------------- #
# ready-made servers
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def editor_wiki_server(nossi_server: Callable[..., str], tmp_path_factory: pytest.TempPathFactory) -> str:
    """Server serving a throwaway wiki seeded with the editor fixture page.

    Use this for tests that save wiki pages, so nothing is written to ``~/wiki``.

    Args:
        nossi_server: Server factory from the ``nossi_server`` fixture.
        tmp_path_factory: pytest-provided factory for temporary directories.

    Returns:
        Base URL of the running server.
    """
    root = make_wiki(
        tmp_path_factory.mktemp("wiki_editor"),
        {
            "editorfixture.md": FIXTURE_DIR / "editor_wiki_page.md",
            "infoletfixture.md": FIXTURE_DIR / "infolet_wiki_page.md",
        },
    )
    return nossi_server(PORT_WIKI, wiki_root=root)


@pytest.fixture(scope="session")
def infolet_page_url(editor_wiki_server: str) -> str:
    """URL of the throwaway infolet fixture page.

    Args:
        editor_wiki_server: Base URL from the ``editor_wiki_server`` fixture.

    Returns:
        Absolute URL to the infolet fixture wiki page.
    """
    return f"{editor_wiki_server}/wiki/infoletfixture"


@pytest.fixture(scope="session")
def editor_page_url(editor_wiki_server: str) -> str:
    """URL of the throwaway editor fixture page.

    Args:
        editor_wiki_server: Base URL from the ``editor_wiki_server`` fixture.

    Returns:
        Absolute URL to the fixture wiki page.
    """
    return f"{editor_wiki_server}/wiki/editorfixture"


@pytest.fixture(scope="session")
def app_server(nossi_server: Callable[..., str], tmp_path_factory: pytest.TempPathFactory) -> str:
    """General-purpose server with a throwaway wiki and a throwaway database.

    Backs the tests that only read the wiki or hit app routes (``/localmarkdown``,
    ``/sse_test_ui``, ``/wiki/clocks``), so they no longer need a hand-started dev
    server on :5000.

    Args:
        nossi_server: Server factory from the ``nossi_server`` fixture.
        tmp_path_factory: pytest-provided factory for temporary directories.

    Returns:
        Base URL of the running server.
    """
    root = make_wiki(
        tmp_path_factory.mktemp("wiki_app"),
        {"clocks.md": FIXTURE_DIR / "clocks_wiki_page.md"},
    )
    database = make_database(LIVE_DATABASE)
    return nossi_server(PORT_APP, database=database, wiki_root=root)
