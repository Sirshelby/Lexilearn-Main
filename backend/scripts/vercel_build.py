"""Build step for the backend service on Vercel.

Vercel runs this after installing dependencies and before the new version
starts serving traffic (see [tool.vercel.scripts] in pyproject.toml), which
makes it the right moment to apply database migrations.

By default migrations only run for production deployments. Otherwise every
preview deployment of an unmerged branch would change the production
database. If you've turned on Neon's preview branching (each preview gets
its own copy of the database), set MIGRATE_PREVIEWS=1 to migrate those too.
"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    target = os.environ.get("VERCEL_ENV", "development")
    if target != "production" and os.environ.get("MIGRATE_PREVIEWS") != "1":
        print(f"Skipping database migrations for a {target} deployment.")
        return 0

    if not (os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("DATABASE_URL")):
        # Better to fail the build than ship an API with no database.
        print("DATABASE_URL is not set. Connect a database to this project first.", file=sys.stderr)
        return 1

    print("Applying database migrations...")
    return subprocess.call([sys.executable, "-m", "alembic", "upgrade", "head"])


if __name__ == "__main__":
    sys.exit(main())
