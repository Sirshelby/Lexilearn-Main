from tests.conftest import PASSWORD, auth_header, register


async def test_register_creates_account_and_first_learner(client) -> None:
    data = await register(client, learner_name="Tobi", learner_age_band="8-10", timezone="Africa/Lagos")
    assert data["token_type"] == "bearer"
    learner = data["user"]["learners"][0]
    assert learner["name"] == "Tobi"
    assert learner["timezone"] == "Africa/Lagos"
    assert learner["preferences"]["font"] == "lexend"  # defaults filled in
    assert "lexilearn_refresh" in client.cookies


async def test_duplicate_email_is_rejected(client) -> None:
    await register(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "PARENT@example.com", "password": PASSWORD, "display_name": "Someone"},
    )
    assert response.status_code == 409


async def test_weak_password_is_rejected(client) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "aaaaaaaaaa", "display_name": "A"},
    )
    assert response.status_code == 422


async def test_login_and_me(client) -> None:
    await register(client)
    bad = await client.post(
        "/api/v1/auth/login", json={"email": "parent@example.com", "password": "nope-nope-nope"}
    )
    assert bad.status_code == 401

    good = await client.post("/api/v1/auth/login", json={"email": "parent@example.com", "password": PASSWORD})
    assert good.status_code == 200
    me = await client.get("/api/v1/auth/me", headers=auth_header(good.json()))
    assert me.status_code == 200
    assert me.json()["email"] == "parent@example.com"


async def test_protected_routes_need_a_token(client) -> None:
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer junk"})).status_code == 401


async def test_refresh_rotates_and_detects_reuse(client) -> None:
    await register(client)
    old_cookie = client.cookies.get("lexilearn_refresh")

    first = await client.post("/api/v1/auth/refresh")
    assert first.status_code == 200
    assert client.cookies.get("lexilearn_refresh") != old_cookie

    # Replaying the old refresh token should fail and revoke everything.
    client.cookies.set("lexilearn_refresh", old_cookie, path="/api/v1/auth")
    replay = await client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401


async def test_logout_revokes_refresh_token(client) -> None:
    await register(client)
    cookie = client.cookies.get("lexilearn_refresh")
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    client.cookies.set("lexilearn_refresh", cookie, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_login_is_rate_limited(client) -> None:
    await register(client)
    codes = []
    for _ in range(10):
        r = await client.post(
            "/api/v1/auth/login", json={"email": "parent@example.com", "password": "wrong-password"}
        )
        codes.append(r.status_code)
    assert 429 in codes
