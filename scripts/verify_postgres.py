"""
Automated verification of Mend backend against a real PostgreSQL instance.
Runs:
1. Database connectivity check
2. Alembic upgrade head on an empty database
3. Alembic check for zero schema drift against SQLAlchemy models
4. Full pytest test suite with TEST_DATABASE_URL pointing to PostgreSQL
"""
import os
import sys
import subprocess
import asyncio
import asyncpg
from pathlib import Path

PG_URL = os.getenv("TEST_DATABASE_URL") or "postgresql+asyncpg://postgres@127.0.0.1:5432/mend_test"
RAW_PG_URL = PG_URL.replace("postgresql+asyncpg://", "postgresql://")
BASE_URL = RAW_PG_URL.rsplit("/", 1)[0] + "/postgres"
EMPTY_DB = "mend_empty_test"

async def prepare_empty_db():
    print(f"Connecting to Postgres at {BASE_URL}...")
    conn = await asyncpg.connect(BASE_URL)
    await conn.execute(f"DROP DATABASE IF EXISTS {EMPTY_DB};")
    await conn.execute(f"CREATE DATABASE {EMPTY_DB};")
    await conn.close()
    print(f"Created clean database: {EMPTY_DB}")

def main():
    asyncio.run(prepare_empty_db())

    repo_root = Path(__file__).resolve().parent.parent
    alembic_ini = repo_root / "backend" / "alembic.ini"
    empty_db_url = PG_URL.rsplit("/", 1)[0] + f"/{EMPTY_DB}"

    print(f"\n--- Running Alembic upgrade head on empty DB ({empty_db_url}) ---")
    env = os.environ.copy()
    env["DATABASE_URL"] = empty_db_url
    res_up = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True
    )
    print(res_up.stdout)
    if res_up.returncode != 0:
        print(res_up.stderr)
        sys.exit(res_up.returncode)

    print("\n--- Running Alembic check on empty DB ---")
    res_chk = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "check"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True
    )
    print(res_chk.stdout)
    if res_chk.returncode != 0:
        print(res_chk.stderr)
        sys.exit(res_chk.returncode)

    print("\n--- Running full test suite against PostgreSQL ---")
    env["TEST_DATABASE_URL"] = PG_URL
    res_pt = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        cwd=str(repo_root),
        env=env
    )
    sys.exit(res_pt.returncode)

if __name__ == "__main__":
    main()
