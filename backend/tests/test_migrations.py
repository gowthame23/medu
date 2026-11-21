import os
import tempfile
from pathlib import Path
import pytest
from alembic.config import Config
from alembic import command


def test_alembic_upgrade_head_and_check_no_schema_drift():
    """
    Ensures migration discipline:
    1. Runs all migrations up to head on an empty database.
    2. Runs alembic check to assert autogenerate finds ZERO schema drift against SQLAlchemy models.
    """
    repo_root = Path(__file__).resolve().parent.parent
    ini_path = repo_root / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))

    # Test with clean isolated SQLite database file or postgres test url
    test_db_env = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if test_db_env and "postgres" in test_db_env:
        # If postgres test environment is provided, use alembic test db
        db_url = test_db_env.replace("/mend_test", "/mend_alembic_test")
        os.environ["DATABASE_URL"] = db_url
        command.upgrade(cfg, "head")
        # command.check raises CommandError if any schema drift exists
        command.check(cfg)
    else:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db_url = f"sqlite+aiosqlite:///{tmp_path}"
            os.environ["DATABASE_URL"] = db_url
            command.upgrade(cfg, "head")
            command.check(cfg)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
