from datetime import date

from app.api.deps import llm_provider
from app.llm.base import ChatMessage
from app.services.progress import calculate_streak


class FakeWriter:
    name = "fake"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    async def complete(self, messages: list[ChatMessage], **kwargs) -> str:
        self.calls += 1
        return self.text


async def test_library_passage_when_offline(client, account) -> None:
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/reading/passage",
        headers=account["headers"],
        json={"topic": "cats"},
    )
    body = r.json()
    assert body["source"] == "library"
    assert body["level"] == 1
    assert body["score"] >= 95


async def test_generated_passage_is_checked(app, client, account) -> None:
    hard = FakeWriter(
        "The Expedition\nThe extraordinary astronaut photographed magnificent "
        "constellations through enormous telescopes during the beautiful night."
    )
    app.dependency_overrides[llm_provider] = lambda: hard
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/reading/passage",
        headers=account["headers"],
        json={"topic": "space"},
    )
    assert r.json()["source"] == "library"
    assert hard.calls == 2  # tried twice before giving up

    easy = FakeWriter(
        "Pam and the Cat\nPam has a cat. The cat is fat. Pam and the cat sit on a mat. "
        "The cat naps. Pam pats the cat. It is fun."
    )
    app.dependency_overrides[llm_provider] = lambda: easy
    r = await client.post(
        f"/api/v1/learners/{account['learner_id']}/reading/passage",
        headers=account["headers"],
        json={"topic": "cats"},
    )
    assert r.json()["source"] == "generated"
    assert r.json()["title"] == "Pam and the Cat"


async def test_tts_without_key_tells_client_to_use_browser_voice(client, account) -> None:
    r = await client.post("/api/v1/speech/tts", headers=account["headers"], json={"text": "cat"})
    assert r.status_code == 503


async def test_health(client) -> None:
    r = await client.get("/api/v1/health")
    assert r.json() == {"status": "ok", "tutor": "offline", "speech": "browser"}


def test_streak_counts_back_from_today_or_yesterday() -> None:
    days = {date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 3)}
    assert calculate_streak(days, date(2026, 3, 3)) == 3
    assert calculate_streak(days, date(2026, 3, 4)) == 3  # not practised yet today
    assert calculate_streak(days, date(2026, 3, 5)) == 0
    assert calculate_streak(set(), date(2026, 3, 5)) == 0
