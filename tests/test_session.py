from codepilot.session import SessionStore


def test_session_store_appends_jsonl_events(tmp_path) -> None:
    store = SessionStore.create(tmp_path / "sessions")

    store.append("user_message", {"content": "你好"})
    store.append("assistant_message", {"content": "收到"})

    events = store.read_events()

    assert [event["type"] for event in events] == ["user_message", "assistant_message"]
    assert events[0]["data"] == {"content": "你好"}
    assert events[1]["data"] == {"content": "收到"}
    assert events[0]["timestamp"]
    assert store.path.exists()
