"""Tests for the chat blueprint, focused on LiveKit token authorization."""

from unittest import mock

import Data
from tests.NossiTestCase import NossiTestCase

LIVEKIT_ENV = {
    "LIVEKIT_URL": "wss://livekit.invalid",
    "LIVEKIT_API_KEY": "testkey",
    "LIVEKIT_API_SECRET": "testsecret",
}


class TestLiveKitToken(NossiTestCase):
    """Test cases for /chat/livekit-token authorization and failure modes."""

    def create_app(self):  # type: ignore[no-untyped-def]
        """Extend the base test app with the chat blueprint."""
        app = super().create_app()
        from NossiSite import chat

        app.register_blueprint(chat.views)
        return app

    @mock.patch.object(Data, "DATABASE", "chat_token.db")
    def test_token_requires_login(self) -> None:
        """An anonymous caller is redirected and gets no token."""
        try:
            with self.app.app_context(), mock.patch.dict("os.environ", LIVEKIT_ENV):
                rv = self.client.get("/chat/livekit-token/someroom")
                assert rv.status_code == 302
                assert "/login" in rv.headers["Location"]
                assert b"token" not in rv.data
        finally:
            self.delete("chat_token.db")

    @mock.patch.object(Data, "DATABASE", "chat_token.db")
    def test_token_issued_for_logged_in_user(self) -> None:
        """A logged-in user receives a token bound to their own username."""
        try:
            client = self.register_login()
            with self.app.app_context(), mock.patch.dict("os.environ", LIVEKIT_ENV):
                rv = client.get("/chat/livekit-token/someroom")
                assert rv.status_code == 200, rv.status_code
                payload = rv.get_json()
                assert payload["token"], "empty token"
                assert payload["url"] == "wss://livekit.invalid"
                assert "Anonymous" not in payload["token"]
        finally:
            self.delete("chat_token.db")

    @mock.patch.object(Data, "DATABASE", "chat_token.db")
    def test_token_503_when_unconfigured(self) -> None:
        """Missing LiveKit credentials yield 503, not a 500 from AccessToken(None)."""
        try:
            client = self.register_login()
            env = {"LIVEKIT_URL": "", "LIVEKIT_API_KEY": "", "LIVEKIT_API_SECRET": ""}
            with self.app.app_context(), mock.patch.dict("os.environ", env, clear=False):
                rv = client.get("/chat/livekit-token/someroom")
                assert rv.status_code == 503, rv.status_code
        finally:
            self.delete("chat_token.db")

    @mock.patch.object(Data, "DATABASE", "chat_token.db")
    def test_token_rejects_malformed_room(self) -> None:
        """Room names are validated before anything is signed."""
        try:
            client = self.register_login()
            for room in ("../etc", "room/with/slash", "a" * 200, "room with spaces"):
                with self.app.app_context(), mock.patch.dict("os.environ", LIVEKIT_ENV):
                    rv = client.get(f"/chat/livekit-token/{room}")
                    assert rv.status_code in (400, 404), (room, rv.status_code)
                    assert b"token" not in rv.data, room
        finally:
            self.delete("chat_token.db")

    @mock.patch.object(Data, "DATABASE", "chat_token.db")
    def test_any_logged_in_user_may_join_any_room(self) -> None:
        """Room access stays open between logged-in users, by design."""
        try:
            client = self.register_login()
            with self.app.app_context(), mock.patch.dict("os.environ", LIVEKIT_ENV):
                for room in ("friendsgame", "not-anyone-elses-room", "x"):
                    rv = client.get(f"/chat/livekit-token/{room}")
                    assert rv.status_code == 200, (room, rv.status_code)
        finally:
            self.delete("chat_token.db")


class TestLiveKitAvailability(NossiTestCase):
    """Test cases for the periodic LiveKit availability ping."""

    def setUp(self) -> None:
        """Reset the process-wide LiveKit reachability cache before each test."""
        super().setUp()
        from NossiSite import chat

        chat._livekit_state.checked_at = 0.0
        chat._livekit_state.reachable = False

    def create_app(self):  # type: ignore[no-untyped-def]
        """Extend the base test app with the chat blueprint."""
        app = super().create_app()
        from NossiSite import chat

        app.register_blueprint(chat.views)
        return app

    @mock.patch.object(Data, "DATABASE", "chat_avail.db")
    def test_chat_page_hides_join_when_server_down(self) -> None:
        """No Join control is rendered when the ping says LiveKit is unreachable."""
        try:
            client = self.register_login()
            with self.app.app_context(), mock.patch.dict("os.environ", LIVEKIT_ENV):
                from NossiSite import chat

                with mock.patch.object(chat, "_ping_livekit", return_value=False):
                    rv = client.get("/chat/")
                    assert rv.status_code == 200
                    body = rv.get_data(as_text=True)
                    assert "join-video-btn" not in body
        finally:
            self.delete("chat_avail.db")

    @mock.patch.object(Data, "DATABASE", "chat_avail.db")
    def test_chat_page_shows_join_when_server_up(self) -> None:
        """The Join control is rendered when the ping succeeds."""
        try:
            client = self.register_login()
            with self.app.app_context(), mock.patch.dict("os.environ", LIVEKIT_ENV):
                from NossiSite import chat

                with mock.patch.object(chat, "_ping_livekit", return_value=True):
                    rv = client.get("/chat/")
                    assert rv.status_code == 200
                    assert "join-video-btn" in rv.get_data(as_text=True)
        finally:
            self.delete("chat_avail.db")

    @mock.patch.object(Data, "DATABASE", "chat_avail.db")
    def test_chat_page_hides_join_without_credentials(self) -> None:
        """Credentials alone are not enough; the server must actually answer."""
        try:
            client = self.register_login()
            env = {"LIVEKIT_URL": "wss://livekit.invalid", "LIVEKIT_API_KEY": "k", "LIVEKIT_API_SECRET": "s"}
            with self.app.app_context():
                from NossiSite import chat

                with (
                    mock.patch.dict("os.environ", env, clear=False),
                    mock.patch.object(chat, "_ping_livekit", return_value=False),
                ):
                    rv = client.get("/chat/")
                    assert "join-video-btn" not in rv.get_data(as_text=True)
        finally:
            self.delete("chat_avail.db")
