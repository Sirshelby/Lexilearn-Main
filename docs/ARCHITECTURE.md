# Architecture

This document explains how LexiLearn fits together and why I made the choices I did. It's also where I've written down what will need to change as usage grows, so those decisions aren't lost.

## Goals

1. **Correct phonics.** Learners with dyslexia are the people most hurt by a tool that teaches something wrong. If the app says a word is decodable at level 1, it must be.
2. **Calm and readable.** Every screen should be usable at large text sizes, with any of the supported fonts and backgrounds.
3. **Safe for children.** Minimal personal data, accounts owned by adults, and an AI tutor that stays on topic.
4. **Cheap to run, and still useful without paid APIs.** The AI and premium voices make it better, but the app must still work if either is missing or down.
5. **Able to grow** without a rewrite: more learners, schools, more content.

## Overview

```
Browser (React SPA)
   |  same origin, HTTPS
   v
nginx  ---- serves static files (hashed, cached forever)
   |  /api/*
   v
FastAPI (uvicorn workers)
   |-- api/routes      HTTP layer: auth, validation, ownership checks
   |-- services        practice, progress, tutor, reading, speech
   |-- literacy        rule engine (pure Python, no I/O)
   |-- llm             provider interface -> OpenAI-compatible API | offline
   |
   +--> PostgreSQL     accounts, learners, progress, sessions, chats
   +--> LLM API        tutor replies, story drafts (optional)
   +--> ElevenLabs     speech, cached on disk (optional)
```

The frontend and API are served from one origin. With Docker that's nginx; on Vercel the project has two services and `vercel.json` routes `/api/*` to the backend and everything else to the frontend (see [DEPLOYING.md](DEPLOYING.md)). Either way the refresh cookie is first-party, CORS isn't needed in production, and there's one domain to secure.

## Key decisions

### FastAPI instead of Flask

The prototype was Flask. I moved to FastAPI mainly for two reasons. First, the request and response schemas are typed Pydantic models, so bad input is rejected before it reaches any logic. The prototype crashed on most endpoints partly because nothing checked what came in or went out. Second, it's async: the slowest thing the API does is wait on the LLM (often several seconds), and an async server can keep serving other learners during that wait. The automatic OpenAPI docs at `/docs` were a bonus.

The trade-off is that async SQLAlchemy is a little more awkward than the sync version, and every database call needs `await`.

### A rule engine for phonics, the LLM for language

This is the most important decision in the project. The `literacy` package works out graphemes, syllables, syllable types and phonics patterns with explicit rules, and maps each pattern to the level where it's taught. It has no network or database access, so it's fast and easy to test.

The LLM is used for things rules are bad at: conversation, explanations, writing a story about dinosaurs. But it is never trusted to judge decodability. When it writes a story, the rule engine checks it; below 95% decodable at the learner's level, it's retried once and then replaced with a hand-written passage. This "AI proposes, rules verify" pattern means a model having a bad day can't put a too-hard text in front of a learner.

The engine follows the division rules taught in OG programmes (VC/CV, V/CV, VC/V, V/V, consonant-le, suffix first). The weak spot is VC/V, which depends on vocabulary; see "Known limitations".

### The curriculum lives in code

`literacy/curriculum.py` holds the scope and sequence: levels, skills, practice words, heart words, library passages. Keeping it in code means it's versioned with the app, reviewed in pull requests, and covered by tests that check every word against the engine. The cost is that changing content needs a deploy. If a non-developer content team appears, this is the module to move into the database, with the same tests running as a validation step on save.

### Talking to the LLM over plain HTTP

Rather than the `openai` SDK, `llm/openai_compat.py` calls the chat completions endpoint with `httpx`. The prototype broke when the SDK changed its interface, and the REST endpoint has been stable for years. It also means one class works with OpenAI, Azure, OpenRouter or a self-hosted model, chosen by `LLM_BASE_URL`. Providers implement a small `LLMProvider` protocol, so adding a different API is one class.

If the provider fails (timeout, 5xx after retries), the tutor falls back to the offline provider instead of showing an error. The reply is simpler but still correct, because it's generated from the phonics engine.

### Auth: short access tokens and rotating refresh tokens

- Passwords are hashed with Argon2id.
- The access token is a JWT valid for 30 minutes, kept only in memory in the browser (never in localStorage, so an XSS bug can't steal a long-lived credential).
- The refresh token is an httpOnly, SameSite=Lax cookie scoped to `/api/v1/auth`. Each one is stored in `refresh_tokens` and works exactly once. Using an already-used token signs the user out everywhere, which is how stolen tokens get detected.
- Login is rate-limited per IP and email, and gives the same error for unknown emails and wrong passwords.

### Accounts own learners

An account is an adult (parent or teacher) or an older learner. Progress belongs to **learner profiles**, not accounts. This matches how the app is actually used (one parent, two children; one tutor, a whole caseload) and keeps children's data minimal: a first name, an optional age band, a timezone. Every learner endpoint goes through `get_owned_learner`, which returns 404 (not 403) for someone else's learner so ids can't be probed. `tests/test_access_control.py` tries every learner endpoint from a second account.

Reading preferences are a JSON column validated by a Pydantic model, so adding a setting doesn't need a migration.

### Grading on the server

A practice session is created server-side with its items and correct answers. The browser gets the items without answers, submits each answer, and gets feedback back. Only the first answer to each item counts. One honest caveat: for listening items the browser has to know the word in order to speak it, so a determined learner could find it in dev tools. That's acceptable here, since this is practice, not an exam.

### Running serverless as well as in a container

I wanted the same code to run in Docker and on Vercel, so the differences live in configuration rather than in two versions of the app. When `VERCEL=1` is set, or the database URL points at a connection pooler:

- the engine stops keeping database connections open (an instance can be frozen at any moment, and the pooler does the pooling)
- asyncpg's prepared statement cache is turned off, because PgBouncer in transaction mode can run each transaction on a different server connection
- migrations move to the build step (`scripts/vercel_build.py`), which only migrates production unless preview branching is turned on

Hosting providers' `postgres://...?sslmode=require` URLs are normalised in `core/config.py`, so a connection string can be pasted in as it comes. I tested the pooler setup against a real PgBouncer; DEPLOYING.md has the results.

Two pieces of state that used to live in the process had to move. Rate limit counts go to Redis over Upstash's HTTP API when it's configured (HTTP rather than the Redis protocol, so there are no connections to manage). The speech cache moved from disk into a Postgres table, because serverless functions have no permanent disk, and adding another storage service didn't seem worth it at this size.

### Mastery rule

A skill is mastered when the learner has completed at least three sessions and the last three average 85% or more. OG practice values consistency over a single good day. A learner is flagged as struggling when their last three sessions are all under 60%, and the dashboard then suggests reviewing the previous skill. The thresholds are constants at the top of `services/progress.py` so they're easy to tune once there's real data.

## Data model

```
users 1---* learners 1---* skill_progress      (one row per learner per skill)
  |               |--------* practice_sessions (items + answers as JSON)
  |               '--------* conversations 1---* messages
  '---* refresh_tokens

tts_clips   (speech audio keyed by a hash of text + voice; short texts only)
```

All primary keys are UUIDs, so ids can't be guessed and rows can be created on different servers without coordination. Timestamps go through a `UTCDateTime` type that always stores UTC and always returns timezone-aware values, which avoids naive/aware comparison bugs (SQLite drops timezone info). Streaks are calculated in each learner's own timezone.

## Frontend

- **Server state** goes through TanStack Query (caching, retries, invalidation after practice). **UI state** stays in components.
- **Two contexts:** `AuthContext` (session, active learner) and `PreferencesContext` (applies the learner's reading settings to `<html>` as data attributes and CSS variables, and saves changes with a short debounce).
- **All sizes are in rem**, and the text size setting sets the root font size, so the whole interface scales with it.
- **Design.** The visual identity comes from OG letter tiles: plain tiles for consonants, salmon tiles for vowels, with a coloured bar under each syllable showing its type. The rest of the interface stays quiet. Readability follows the British Dyslexia Association style guide: no pure white by default, dark grey text, generous spacing, no italics or all caps, left aligned.
- **Fonts are self-hosted** through Fontsource (the prototype tried to load OpenDyslexic from Google Fonts, which doesn't host it).
- **Speech.** The app asks the API whether premium voices are configured and uses them for single words if so, caching clips in the browser. Otherwise, and always for read-along (which needs word timings), it uses the Web Speech API.

## Security checklist

| Concern | How it's handled |
| --- | --- |
| Secrets | Only from the environment; `.env` is git-ignored; the app refuses to start in production with the default secret |
| Passwords | Argon2id; minimum length and a small common-password check |
| Sessions | Short in-memory access token; rotating httpOnly refresh cookie with reuse detection |
| Access control | Ownership check on every learner-scoped route; 404 for others' data; tested |
| Abuse of paid APIs | Tutor, story and TTS endpoints need auth and are rate-limited per user; input lengths capped |
| Error leakage | A global handler logs the details and returns a generic 500 |
| Browser hardening | nginx sets a strict CSP (self only), nosniff, a referrer policy and a permissions policy |
| Children's data | First name and age band only; prompts forbid asking for personal details |

## Scaling plan

What I'd change, roughly in the order it would be needed:

1. **More than one instance.** Most of this is done: rate limits go to Redis when it's configured, the speech cache is in Postgres, and on Vercel migrations run once per deploy in the build. For Docker with several replicas, move `alembic upgrade head` out of the container start into a release job.
2. **Speech at scale.** If the `tts_clips` table grows large, move the audio to object storage (Vercel Blob, S3 or R2) behind a CDN. The cache keys stay the same.
3. **Tutor latency.** Stream replies with server-sent events so text appears as it's generated. The provider interface would gain a `stream()` method.
4. **Database growth.** `messages` and `practice_sessions` will be the big tables. Both already have indexes on their access paths. The next steps are archiving old sessions into a summary table, and a read replica for dashboards.
5. **Schools.** Add organisations and classes above accounts, with teacher and admin roles. This is also where the 30-learners-per-account limit gets replaced.
6. **Observability.** Structured JSON logs, request ids, and OpenTelemetry traces around LLM and TTS calls, which are the expensive and slow parts.
7. **Content at scale.** Move the curriculum to the database with an editor, keeping the decodability tests as validation.

## Known limitations

- **VC/V division** relies on a short word list (`VC_V_WORDS`). Using CMUdict to check whether the open-syllable reading exists would make this properly general.
- **Ambiguous spellings** like `ow` (snow and cow) and `ea` (bead and bread) are tagged by pattern, not pronunciation. That's fine for decodability, but it means the engine can't say which sound to use.
- **A few words are wrong** (for example "nothing" splits as noth-ing). The `OVERRIDES` table in `syllables.py` is there for exactly these, and every fix should come with a test in `tests/test_syllables.py`.
- **Email verification and password reset** aren't built yet.
