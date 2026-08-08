from app.services.conversation_service import ConversationService


def test_add_and_get_messages_roundtrip(tmp_path):
    service = ConversationService(db_path=str(tmp_path / "conversation.db"))

    service.add_message(role="user", content="What does the report say about KIT?")
    service.add_message(
        role="assistant",
        content="KIT was not detected.",
        sources=[{"filename": "N149.pdf", "page_number": 1, "similarity_score": 0.82}],
        retrieved_chunks=None,
        context_found=True,
    )

    messages = service.get_all_messages()

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "What does the report say about KIT?"
    assert messages[0].sources is None
    assert messages[1].role == "assistant"
    assert messages[1].sources == [{"filename": "N149.pdf", "page_number": 1, "similarity_score": 0.82}]
    assert messages[1].context_found is True


def test_messages_are_returned_in_insertion_order(tmp_path):
    service = ConversationService(db_path=str(tmp_path / "conversation.db"))

    service.add_message(role="user", content="first")
    service.add_message(role="assistant", content="second")
    service.add_message(role="user", content="third")

    messages = service.get_all_messages()

    assert [m.content for m in messages] == ["first", "second", "third"]


def test_get_all_messages_empty_when_nothing_persisted(tmp_path):
    service = ConversationService(db_path=str(tmp_path / "conversation.db"))

    assert service.get_all_messages() == []


def test_clear_removes_all_messages_and_returns_count(tmp_path):
    service = ConversationService(db_path=str(tmp_path / "conversation.db"))

    service.add_message(role="user", content="one")
    service.add_message(role="assistant", content="two")

    deleted_count = service.clear()

    assert deleted_count == 2
    assert service.get_all_messages() == []


def test_conversation_persists_across_service_instances(tmp_path):
    # Simulates a backend restart: a new ConversationService instance
    # pointed at the same db file must see previously persisted messages.
    db_path = str(tmp_path / "conversation.db")

    first_instance = ConversationService(db_path=db_path)
    first_instance.add_message(role="user", content="Does this survive a restart?")

    second_instance = ConversationService(db_path=db_path)
    messages = second_instance.get_all_messages()

    assert len(messages) == 1
    assert messages[0].content == "Does this survive a restart?"


def test_is_reachable_true_for_valid_store(tmp_path):
    service = ConversationService(db_path=str(tmp_path / "conversation.db"))
    assert service.is_reachable() is True
