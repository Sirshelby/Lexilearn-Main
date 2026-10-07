from app.literacy.decodability import analyze_word
from app.literacy.syllables import split_syllables


def correct_answer(item: dict) -> str:
    """Work out the right answer the same way a learner would, from what's on screen."""
    kind = item["kind"]
    if kind in {"listen_choose", "spell"}:
        return item["say"]
    if kind == "count_sounds":
        return str(analyze_word(item["word"]).sound_count)
    return "-".join(split_syllables(item["word"]))


async def run_session(client, account, score_all: bool = True, skill_code: str | None = None) -> dict:
    base = f"/api/v1/learners/{account['learner_id']}/practice/sessions"
    h = account["headers"]
    started = await client.post(base, headers=h, json={"skill_code": skill_code} if skill_code else {})
    assert started.status_code == 201, started.text
    session = started.json()

    for item in session["items"]:
        answer = correct_answer(item) if score_all else "zzz"
        r = await client.post(
            f"{base}/{session['id']}/answers", headers=h, json={"item_index": item["index"], "answer": answer}
        )
        assert r.status_code == 200
        assert r.json()["correct"] is score_all

    done = await client.post(f"{base}/{session['id']}/complete", headers=h)
    assert done.status_code == 200
    return {"session": session, "result": done.json()}


async def test_items_do_not_leak_answers(client, account) -> None:
    started = await client.post(
        f"/api/v1/learners/{account['learner_id']}/practice/sessions", headers=account["headers"], json={}
    )
    session = started.json()
    assert session["skill_code"] == "1.1"
    assert len(session["items"]) == 8
    for item in session["items"]:
        assert "answer" not in item
        if item["kind"] == "count_sounds":
            assert item["say"] is None


async def test_three_good_sessions_master_a_skill(client, account) -> None:
    for _ in range(2):
        outcome = await run_session(client, account)
        assert outcome["result"]["mastered_now"] is False
    final = await run_session(client, account)
    assert final["result"]["accuracy"] == 100.0
    assert final["result"]["mastered_now"] is True
    assert final["result"]["next_skill_code"] == "1.2"

    progress = await client.get(
        f"/api/v1/learners/{account['learner_id']}/progress", headers=account["headers"]
    )
    body = progress.json()
    assert body["skills_mastered"] == 1
    assert body["current_skill"]["code"] == "1.2"
    assert body["streak_days"] == 1
    assert body["sessions_this_week"] == 3


async def test_only_first_answer_counts(client, account) -> None:
    base = f"/api/v1/learners/{account['learner_id']}/practice/sessions"
    h = account["headers"]
    session = (await client.post(base, headers=h, json={})).json()
    item = session["items"][0]
    await client.post(f"{base}/{session['id']}/answers", headers=h, json={"item_index": 0, "answer": "wrong"})
    retry = await client.post(
        f"{base}/{session['id']}/answers", headers=h, json={"item_index": 0, "answer": correct_answer(item)}
    )
    assert retry.json()["correct"] is True  # feedback still says it's right...
    done = (await client.post(f"{base}/{session['id']}/complete", headers=h)).json()
    assert done["correct"] == 0  # ...but the score only counts the first try


async def test_cannot_skip_ahead_or_finish_twice(client, account) -> None:
    base = f"/api/v1/learners/{account['learner_id']}/practice/sessions"
    h = account["headers"]
    locked = await client.post(base, headers=h, json={"skill_code": "6.1"})
    assert locked.status_code == 409

    session = (await client.post(base, headers=h, json={})).json()
    assert (await client.post(f"{base}/{session['id']}/complete", headers=h)).status_code == 200
    assert (await client.post(f"{base}/{session['id']}/complete", headers=h)).status_code == 409


async def test_struggling_learner_gets_a_review_suggestion(client, account) -> None:
    for _ in range(3):
        await run_session(client, account)  # master 1.1
    for _ in range(3):
        await run_session(client, account, score_all=False)  # struggle on 1.2
    body = (
        await client.get(f"/api/v1/learners/{account['learner_id']}/progress", headers=account["headers"])
    ).json()
    assert any("Short a" in rec for rec in body["recommendations"])
