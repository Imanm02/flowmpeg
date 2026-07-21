from flowmpeg.ui.session import UiSession


def test_ui_sessions_create_distinct_request_tokens() -> None:
    first = UiSession.create()
    second = UiSession.create()

    assert first.token != second.token
    assert len(first.token) >= 32


def test_ui_session_checks_exact_request_token() -> None:
    session = UiSession("local-test-token")

    assert session.accepts("local-test-token") is True
    assert session.accepts("different-token") is False
    assert session.accepts(None) is False
