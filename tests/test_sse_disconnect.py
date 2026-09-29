"""Regression tests for SSE connection cleanup.

The production failure mode: the ``/sse_updates`` generator blocked forever in an
untimed ``queue.get()``, so when a client vanished the greenlet never observed the
disconnect, never ran its ``finally``, and never returned its gunicorn pool slot.
The worker's ``Pool(worker_connections)`` (default 1000) slowly saturated, at which
point gevent's ``StreamServer`` stopped calling ``accept()`` entirely and the whole
site stopped answering -- while the process still looked healthy in ``ps``.

These tests drive a real socket so the disconnect is observed the way nginx observes
it: the peer goes away and nobody calls ``close()`` on the server side.
"""

import socket
import time
from typing import TYPE_CHECKING, Any

import pytest
from flask import Flask
from gevent import monkey

if TYPE_CHECKING:
    from collections.abc import Iterator

monkey.patch_all()

from gevent.pywsgi import WSGIServer  # noqa: E402

from NossiSite import socks  # noqa: E402

# How long a well-behaved server may take to notice a dead peer. The heartbeat
# interval bounds this; the test allows a generous multiple for slow CI.
DISCONNECT_DEADLINE = 15.0


def _free_port() -> int:
    """Return a currently free TCP port on the loopback interface."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _sse_app() -> Flask:
    """Build a minimal Flask app serving only the SSE blueprint."""
    app = Flask(__name__)
    app.register_blueprint(socks.views)
    return app


class _ActiveBodies:
    """Count response bodies that are still open.

    A gevent greenlet -- and therefore one gunicorn pool slot -- stays occupied for
    as long as its response iterator is open. Counting open bodies is the closest
    faithful proxy for "pool slots still held" that does not depend on gevent
    internals.
    """

    def __init__(self, app: Any) -> None:
        """Wrap ``app`` so open response bodies are counted.

        Args:
            app: The WSGI application to wrap.
        """
        self._app = app
        self.count = 0

    def __call__(self, environ: dict[str, Any], start_response: Any) -> Any:
        """Serve one request, counting it until its body is exhausted.

        Args:
            environ: WSGI environment.
            start_response: WSGI start_response callable.

        Returns:
            A wrapped response iterable.
        """
        self.count += 1
        body = self._app(environ, start_response)

        def counting_body() -> Any:
            """Yield from the response, releasing the slot once it is exhausted."""
            try:
                yield from body
            finally:
                self.count -= 1

        return counting_body()


def _read_until_idle(conn: socket.socket, idle: float) -> bytes:
    """Read from ``conn`` until it goes quiet for ``idle`` seconds or time runs out.

    Args:
        conn: Connected socket to read from.
        idle: Idle time after which reading is considered finished.

    Returns:
        Everything read from the socket.
    """
    conn.settimeout(idle)
    buf = b""
    deadline = time.time() + DISCONNECT_DEADLINE
    while time.time() < deadline:
        try:
            chunk = conn.recv(4096)
        except OSError:
            # Covers the read timeout and a reset by a vanished peer.
            break
        if not chunk:
            break
        buf += chunk
    return buf


def _wait_until(predicate: Any, timeout: float) -> bool:
    """Poll ``predicate`` until it is true or ``timeout`` seconds elapse.

    Args:
        predicate: Zero-argument callable to poll.
        timeout: Seconds to wait before giving up.

    Returns:
        True if the predicate became true in time, False otherwise.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return bool(predicate())


@pytest.fixture(autouse=True)
def _clean_hub() -> Iterator[None]:
    """Ensure a leaked hub registration from one test cannot mask another's failure."""
    socks.connected_hubs.clear()
    yield
    socks.connected_hubs.clear()


@pytest.fixture
def fast_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shorten the keepalive interval so tests do not wait on the production cadence.

    The mechanism under test is the bounded wait, not the specific interval; the
    default is asserted separately in ``test_heartbeat_interval_is_bounded``.
    """
    monkeypatch.setattr(socks, "SSE_HEARTBEAT_INTERVAL", 0.25)


def test_heartbeat_interval_is_bounded() -> None:
    """The keepalive interval must stay short enough to reclaim slots promptly.

    Disconnecting a client takes up to two heartbeats to detect, so this value is
    the ceiling on how long a dead peer can hold a gunicorn pool slot.
    """
    assert 0 < socks.SSE_HEARTBEAT_INTERVAL <= 30.0, (
        f"SSE_HEARTBEAT_INTERVAL={socks.SSE_HEARTBEAT_INTERVAL} is too long; a dead "
        f"client would hold its gunicorn pool slot for minutes"
    )


@pytest.mark.usefixtures("fast_heartbeat")
def test_sse_client_disconnect_is_reaped() -> None:
    """A vanished ``/sse_updates`` client is noticed and its pool slot returned.

    This is the regression test for the outage: without a bounded wait and a
    write-side disconnect check, the server keeps the greenlet -- and its pool slot --
    alive forever, and the accept queue eventually jams.
    """
    tracker = _ActiveBodies(_sse_app())
    port = _free_port()
    server = WSGIServer(("127.0.0.1", port), tracker, log=None)
    server.start()

    try:
        conn = socket.create_connection(("127.0.0.1", port), timeout=DISCONNECT_DEADLINE)
        conn.sendall(b"GET /sse_updates HTTP/1.1\r\nHost: localhost\r\n\r\n")

        # The ": connected" preamble proves the generator is running and has
        # registered its hub queue.
        first = _read_until_idle(conn, idle=1.0)
        assert b"connected" in first, f"no SSE preamble received, got {first!r}"
        assert len(socks.connected_hubs) == 1, "SSE client did not register a hub queue"

        # Vanish the way a closed browser tab does: no shutdown handshake, and
        # crucially nothing on the server side calls close() for us.
        conn.close()

        # The server must notice on its own and free the slot.
        reaped = _wait_until(lambda: not socks.connected_hubs, DISCONNECT_DEADLINE)
        assert reaped, (
            f"SSE hub still holds {len(socks.connected_hubs)} queue(s) "
            f"{DISCONNECT_DEADLINE}s after the client disconnected -- the "
            f"generator is leaking its gunicorn pool slot"
        )

        bodies_released = _wait_until(lambda: tracker.count == 0, DISCONNECT_DEADLINE)
        assert bodies_released, f"{tracker.count} response body/bodies still open after disconnect"
    finally:
        server.stop()


def test_sse_test_endpoint_disconnect_is_reaped() -> None:
    """The ``/sse_test`` clock stream releases its slot on disconnect too.

    It has the same unbounded ``while True`` shape as the hub, so it leaks the same
    way and needs the same guard.
    """
    tracker = _ActiveBodies(_sse_app())
    port = _free_port()
    server = WSGIServer(("127.0.0.1", port), tracker, log=None)
    server.start()

    try:
        conn = socket.create_connection(("127.0.0.1", port), timeout=DISCONNECT_DEADLINE)
        conn.sendall(b"GET /sse_test HTTP/1.1\r\nHost: localhost\r\n\r\n")

        first = _read_until_idle(conn, idle=1.0)
        assert b"data:" in first, f"no clock payload received, got {first!r}"
        assert tracker.count == 1, "/sse_test request did not start a response body"

        conn.close()

        reaped = _wait_until(lambda: tracker.count == 0, DISCONNECT_DEADLINE)
        assert reaped, f"/sse_test response body still open {DISCONNECT_DEADLINE}s after disconnect"
    finally:
        server.stop()
