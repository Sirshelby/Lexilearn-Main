from app.api.deps import llm_provider
from app.llm.base import ChatMessage, LLMError
from app.services.tutor import clean_reply


class BrokenProvider:
    name = "broken"

    async def complete(self, messages: list[ChatMessage], **kwargs) -> str:
        raise LLMError("down")


async def _new_conversation(client, account) -> str:
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/tutor/conversations", headers=account["headers"]
    )
    assert r.status_code == 201
    return r.json()["id"]


async def test_offline_tutor_breaks_words_into_syllables(client, account) -> None:
    convo = await _new_conversation(client, account)
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/tutor/conversations/{convo}/messages",
        headers=account["headers"],
        json={"content": 'How do I read "rabbit"?'},
    )
    assert r.status_code == 200
    assert "rab-bit" in r.json()["reply"]["content"]

    detail = await client.get(
        f"/api/v1/learners/{account['learner_id']}/tutor/conversations/{convo}", headers=account["headers"]
    )
    body = detail.json()
    assert body["title"] == "How do I read rabbit"
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]


async def test_falls_back_when_provider_is_down(app, client, account) -> None:
    app.dependency_overrides[llm_provider] = lambda: BrokenProvider()
    convo = await _new_conversation(client, account)
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/tutor/conversations/{convo}/messages",
        headers=account["headers"],
        json={"content": "spell table"},
    )
    assert r.status_code == 200
    assert "ta-ble" in r.json()["reply"]["content"]


async def test_message_length_is_limited(client, account) -> None:
    convo = await _new_conversation(client, account)
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/tutor/conversations/{convo}/messages",
        headers=account["headers"],
        json={"content": "a" * 1001},
    )
    assert r.status_code == 422


def test_clean_reply_strips_things_tts_reads_badly() -> None:
    raw = "**Great job!** 🎉\n- Say /sh/ \n# Next"
    assert clean_reply(raw) == "Great job! \nSay /sh/ \nNext"
