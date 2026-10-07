"""One account must never be able to see or change another account's learners."""

import pytest

from tests.conftest import auth_header, register


@pytest.fixture
async def two_accounts(client):
    a = await register(client, email="a@example.com")
    b = await register(client, email="b@example.com")
    return a, b


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/learners/{id}"),
        ("patch", "/learners/{id}"),
        ("delete", "/learners/{id}"),
        ("get", "/learners/{id}/progress"),
        ("post", "/learners/{id}/practice/sessions"),
        ("get", "/learners/{id}/tutor/conversations"),
        ("post", "/learners/{id}/tutor/conversations"),
        ("post", "/learners/{id}/reading/passage"),
    ],
)
async def test_cannot_touch_someone_elses_learner(client, two_accounts, method, path) -> None:
    a, b = two_accounts
    learner_a = a["user"]["learners"][0]["id"]
    url = "/api/v1" + path.format(id=learner_a)
    kwargs = {"headers": auth_header(b)}
    if method in {"post", "patch"}:
        kwargs["json"] = {}
    response = await getattr(client, method)(url, **kwargs)
    assert response.status_code == 404


async def test_cannot_read_someone_elses_conversation(client, two_accounts) -> None:
    a, b = two_accounts
    learner_a = a["user"]["learners"][0]["id"]
    learner_b = b["user"]["learners"][0]["id"]
    convo = await client.post(f"/api/v1/learners/{learner_a}/tutor/conversations", headers=auth_header(a))
    convo_id = convo.json()["id"]
    # Even through B's own learner id, A's conversation isn't reachable.
    response = await client.get(
        f"/api/v1/learners/{learner_b}/tutor/conversations/{convo_id}", headers=auth_header(b)
    )
    assert response.status_code == 404
