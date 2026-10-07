# LexiLearn

LexiLearn is a reading tutor for children and adults with dyslexia. It teaches reading the way structured literacy programmes (Orton-Gillingham and the approaches based on it) do: one sound pattern at a time, in a fixed order, with lots of hearing, saying and building words, and nothing moves on until the learner is secure.

It's my final year project. It started as a prototype in Flask and vanilla JavaScript, and this is a full rewrite of it. The [architecture doc](docs/ARCHITECTURE.md) explains the design decisions and what I'd change as it grows.

## What it does

- **Practice sessions** for each of 33 skills across 8 levels, from short vowels up to consonant-le and soft c. Each session mixes listening, spelling, counting sounds and splitting syllables. Answers are graded on the server, and a skill counts as mastered after three sessions in a row averaging 85% or more.
- **Lexi, the AI tutor.** Learners can ask about any word. Lexi knows their level and current skill, keeps replies short and plain so they can be read aloud, and any word in a reply can be tapped to see it broken into letter tiles.
- **Reading room.** Short stories at the learner's level. The AI can write a new one on any topic, but every story is checked by the phonics engine first, and if too many words use patterns the learner hasn't been taught it's rejected and a hand-written one is used instead. Stories can be read aloud with word-by-word highlighting.
- **Word lab.** Shows any word as syllables, coloured by syllable type, with the patterns it uses. Parents and teachers can paste a passage from a book and see what percentage of it a learner can decode at their level.
- **Two games:** a syllable builder and a rhyme catcher.
- **Reading settings per learner:** Lexend, Atkinson Hyperlegible or OpenDyslexic, text size, letter and line spacing, four backgrounds including dark and high contrast, coloured overlays, voice speed. The whole interface scales with the text size, not just paragraphs.
- **Accounts for parents and teachers** that hold several learner profiles. Learners only need a first name. No dates of birth, no full names.

Everything works with no API keys at all. Without an LLM key Lexi runs in an offline mode built on the phonics engine, and without an ElevenLabs key speech uses the browser's built-in voices.

## Tech stack

| Part | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic |
| Database | PostgreSQL in production, SQLite for local development and tests |
| Auth | Argon2 password hashing, short-lived JWT access tokens, rotating refresh tokens in an httpOnly cookie |
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query |
| AI | Any OpenAI-compatible chat API (OpenAI, Azure, OpenRouter, Ollama...) |
| Speech | ElevenLabs with clips cached in Postgres, falling back to the Web Speech API |
| Deployment | Vercel (static frontend, FastAPI as a function, Neon Postgres), or Docker Compose |
| Tooling | uv with a lockfile for Python, npm for the frontend, GitHub Actions for CI |

## Running it

### On Vercel

It deploys as one Vercel project with two services (the frontend and the FastAPI backend), configured in `vercel.json`. See [docs/DEPLOYING.md](docs/DEPLOYING.md) for the steps, the Neon database, the environment variables, and how the serverless setup was tested.

### With Docker

```bash
cp .env.example .env
# edit .env: set SECRET_KEY and POSTGRES_PASSWORD, optionally the API keys
docker compose up --build
```

Then open http://localhost:8080.

### For development

You need [uv](https://docs.astral.sh/uv/) (it installs the right Python version for you) and Node 22+.

```bash
make install    # installs the locked Python and npm dependencies
make api        # API on http://localhost:8000, docs at /docs
make web        # frontend on http://localhost:5173 (in a second terminal)
```

Local development uses SQLite by default, so there's no database to set up. Settings come from environment variables or `backend/.env`; see [.env.example](.env.example) for the full list.

## Tests

```bash
make test       # backend (pytest) and frontend (vitest)
make lint       # ruff, TypeScript and ESLint
```

The backend has 191 tests. The ones I care about most are in `tests/test_curriculum.py`: they check that every practice word in the curriculum is decodable at the level it's taught, and that every library story passes the decodability check. If someone edits the curriculum and adds a word that's too hard, CI fails. There are also access-control tests that try every learner endpoint with another account's ids.

## Project layout

```
backend/
  app/
    literacy/     phonics engine: graphemes, syllables, curriculum, decodability (no I/O)
    llm/          model providers (OpenAI-compatible and offline) and prompts
    services/     practice, progress/mastery, tutor, reading, speech
    api/routes/   HTTP endpoints, thin wrappers around services
    models/       SQLAlchemy tables
    schemas/      Pydantic request/response models
  migrations/     Alembic
  scripts/        Vercel build step (runs migrations)
  tests/
frontend/
  src/
    pages/        one file per screen
    features/     practice items and games
    components/   letter tiles, word card, app shell...
    context/      auth and reading preferences
    lib/          API client, speech, small helpers
    styles/       design tokens and themes, then component styles
docs/
  ARCHITECTURE.md
  DEPLOYING.md
```

## Known limitations

- **Syllable division isn't perfect.** The VC/V rule (cab-in vs ro-bot) depends on whether the open version is a real word, which a rule engine can't know. I use a list of common VC/V words for now. A pronunciation dictionary like CMUdict would fix it properly.
- **Rate limits need Redis to be exact.** Without the Redis variables, each server process (or Vercel instance) keeps its own counts. That's fine for a demo, but connect Upstash before real launch.
- **Read-along highlighting needs the browser voice**, because the premium audio files don't come with word timings.
- **No email verification or password reset yet.** Both need an email provider, which is next on the list.

## What changed from the prototype

The prototype's frontend never called its backend (the chat was keyword matching), most backend endpoints crashed, the decodability checker marked "The cat sat on the mat" as too hard for beginners, the syllable splitter broke vowel teams apart, and progress was kept in a Python dict that was lost on restart. Accounts lived in the browser's localStorage, and the API keys were committed in a `.env` file. All of that is fixed here, and the architecture doc covers how.
