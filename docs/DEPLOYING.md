# Deploying LexiLearn

There are two ways to run LexiLearn in production: on Vercel (what I use), or anywhere that runs Docker. The code is the same for both; it detects Vercel and adjusts itself.

## Vercel

### How it's laid out

LexiLearn deploys as **one Vercel project with two services**, defined in `vercel.json` at the repo root:

```
browser ──> one domain
              ├── /api/*            ──> backend service: FastAPI as one Vercel Function
              │                            ├──> Neon Postgres  (Vercel Marketplace)
              │                            └──> Upstash Redis  (Marketplace, optional)
              └── everything else   ──> frontend service: the Vite build, served from the CDN
```

Vercel builds each service separately and routes requests by path. A service receives the original request path, so FastAPI still sees `/api/v1/...` and its routes didn't need to change. Everything sits on one domain, so the login cookie is first-party and the API doesn't need CORS.

There are no service bindings. Bindings are for server code in one service calling another, and nothing here does that: the frontend is static files, and its API calls come from the learner's browser using relative `/api/v1/...` URLs, which go through the public `/api` route like any other request.

The frontend service has one rewrite of its own: page paths like `/practice` are served `index.html`, so React Router can handle them. It only matches paths without a file extension, and skips the dev server's internal paths (`/@vite`, `/src`, `/node_modules`). A catch-all version broke `vercel dev`, because the JavaScript files were answered with HTML too.

### What changes when it runs on Vercel

The backend was written to run as a long-lived server, and a Vercel Function is different: instances start and stop on demand, can run many copies at once, and have no permanent disk. The code handles this:

| Concern | How it's handled |
| --- | --- |
| Database connections | When `VERCEL=1` (Vercel sets it), connections aren't kept open between requests. Neon's pooler does the pooling. |
| Connection pooler | Neon's pooled URL goes through PgBouncer. The app detects `-pooler` in the host name and turns off asyncpg's prepared statement cache, which otherwise breaks behind PgBouncer. |
| Database URL format | Neon gives `postgres://...?sslmode=require`. The app rewrites it for its async driver automatically. |
| Migrations | Run during the backend's build by `backend/scripts/vercel_build.py` (set in `backend/pyproject.toml`), before the new version goes live, using the direct (unpooled) connection. |
| Speech cache | Stored in Postgres, not on disk. |
| Rate limits | Shared through Redis if it's connected; otherwise each instance keeps its own counts. |
| Time limits | The backend function may run for up to 60 seconds (set in `vercel.json`). The AI client retries once at most, so a slow provider can't run past that. |

### 1. Push the code to GitHub

Push this repository to GitHub. The `.gitignore` keeps `.env` out of git.

### 2. Import it as one project

1. In Vercel, choose **Add New > Project** and import the repository.
2. Vercel finds `vercel.json` and imports it as a **multi-service project**. Leave the root directory as the repository root (not `backend` or `frontend`).
3. Name the project, for example `lexilearn`, and deploy.

**The first build will fail, and that's expected.** The backend's build step stops with "DATABASE_URL is not set", because a production deployment without a database is a mistake. The next step adds one.

### 3. Add the database

1. Open the project and go to the **Storage** tab.
2. Create a **Neon** Postgres database and connect it to the project for all environments.
3. Neon adds `DATABASE_URL` (pooled) and `DATABASE_URL_UNPOOLED` (direct) to the project's environment variables. Both are used.

**Choose the region carefully.** Pick the Neon region closest to your learners. Then set the project's function region to the same place, under **Settings > Functions > Function Region**. Every request opens a new database connection, so any distance between the function and the database is paid on every single request.

### 4. Set the environment variables

Go to **Settings > Environment Variables** and add these. All services in the project share them.

| Name | Value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `SECRET_KEY` | A long random string: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `COOKIE_SECURE` | `true` |
| `LLM_API_KEY` | Your new OpenAI key (optional; without it Lexi uses the offline tutor) |
| `LLM_MODEL` | A model your account can use, for example `gpt-4o-mini` |
| `ELEVENLABS_API_KEY` | Your new ElevenLabs key (optional; without it the browser's voices are used) |

**Optional: shared rate limits.** In the **Storage** tab, add **Upstash Redis** and connect it. It sets `KV_REST_API_URL` and `KV_REST_API_TOKEN`, which the app picks up automatically.

Then go to **Deployments** and redeploy the latest one. The backend service's build log should show `Applying database migrations...`.

### 5. Check it works

- `https://<your-domain>/api/v1/health` should return `{"status": "ok", ...}`.
- `curl -I https://<your-domain>/` should list a `Content-Security-Policy` header.
- Open the site and create an account.

The `/docs` page is switched off in production on purpose.

### Running it locally the Vercel way

```bash
vercel dev -L    # runs both services behind one port, without logging in to Vercel
```

`make api` and `make web` still work too, and are quicker to restart while you're editing.

### Day to day

Pushing to `main` redeploys the whole project. The backend's build applies any new migrations before the new code goes live.

Preview deployments include both services, so a preview's frontend talks to that same preview's backend. Preview builds skip migrations, so an unmerged branch can't change the production database. This means a preview whose branch adds a migration will be running against the old schema. If that's a problem, turn on Neon's preview branching (each preview gets its own copy of the database) and set `MIGRATE_PREVIEWS=1` for the Preview environment.

### Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Build fails with "DATABASE_URL is not set" | The database isn't connected for that environment (step 3). |
| The build log has no "Applying database migrations" line | The backend's build script didn't run. Add `"buildCommand": "python scripts/vercel_build.py"` to the `backend` service in `vercel.json`. |
| Every request returns 500, and the logs say "SECRET_KEY must be set" | `SECRET_KEY` is missing (step 4). |
| Pages load but are blank | A rewrite is serving `index.html` for JavaScript files. Check the frontend service's rewrite in `vercel.json`. |
| You're signed out every time you refresh the page | `COOKIE_SECURE` is wrong, or you're on a different domain from the one you signed in on. |
| Lexi gives simple, offline-style answers | `LLM_API_KEY` is missing or `LLM_MODEL` is wrong. Search the function logs for "LLM request rejected". |
| The first request after a quiet spell is slow | A cold start. This is normal for serverless functions. |

## Docker

```bash
cp .env.example .env    # set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

This runs Postgres, the API and nginx, and serves the app on port 8080. Migrations run when the API container starts. It works on any VPS or container host.

## How the Vercel setup was tested

Before writing this guide I ran the API in Vercel mode (`VERCEL=1`) against PostgreSQL 16 behind PgBouncer in transaction mode. I configured PgBouncer more strictly than Neon (prepared statements disabled, only 3 server connections) and had 25 simulated learners go through the whole app at once: register, three practice sessions, mastering a skill, the tutor, progress, a story, and a token refresh. All 25 passed, with no errors in the logs.

I also checked the failure case. With a kept-open connection pool and the PgBouncer workaround switched off, all 25 failed with "prepared statement does not exist", which is why the workaround is there. The build script was run the same way: it migrated a fresh database through the direct connection, and it skipped migrations for preview builds.

The services setup was run with `vercel dev -L`. API paths reached FastAPI with their full `/api/v1/...` path, page paths like `/practice` got the app, and an unknown `/api` path got FastAPI's 404 rather than the app. In a browser, registering, practising, chatting with Lexi and reloading the page while staying signed in all worked, with no page errors. Two things `vercel dev` can't show are the security headers (it didn't apply them locally) and the build script running, so step 5 checks those on the real deployment.
