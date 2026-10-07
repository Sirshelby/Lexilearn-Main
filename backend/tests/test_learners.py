async def test_add_update_and_delete_learner(client, account) -> None:
    h = account["headers"]
    created = await client.post("/api/v1/learners", headers=h, json={"name": "Kemi", "age_band": "5-7"})
    assert created.status_code == 201
    kemi = created.json()

    patched = await client.patch(
        f"/api/v1/learners/{kemi['id']}",
        headers=h,
        json={"preferences": {"font": "opendyslexic", "theme": "cream", "text_size": 24}},
    )
    assert patched.status_code == 200
    assert patched.json()["preferences"]["font"] == "opendyslexic"
    assert patched.json()["preferences"]["letter_spacing"] == "wide"  # untouched default

    bad = await client.patch(
        f"/api/v1/learners/{kemi['id']}", headers=h, json={"preferences": {"text_size": 90}}
    )
    assert bad.status_code == 422

    listed = await client.get("/api/v1/learners", headers=h)
    assert [learner["name"] for learner in listed.json()] == ["Sam", "Kemi"]

    assert (await client.delete(f"/api/v1/learners/{kemi['id']}", headers=h)).status_code == 204


async def test_cannot_delete_last_learner(client, account) -> None:
    response = await client.delete(f"/api/v1/learners/{account['learner_id']}", headers=account["headers"])
    assert response.status_code == 409
