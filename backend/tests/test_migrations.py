import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


def test_alembic_migrations_from_scratch():
    """Validates that Alembic migrations run cleanly from head down and create all required tables."""
    # Use a clean temporary SQLite database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        sync_url = f"sqlite:///{db_path}"
        
        # Point alembic config to our backend alembic folder
        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic")))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        # Run migration upgrade to head
        command.upgrade(alembic_cfg, "head")

        # Inspect tables created
        engine = create_engine(sync_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            "users",
            "refresh_tokens",
            "family_groups",
            "family_members",
            "family_invitations",
            "expense_categories",
            "daily_logs",
            "daily_log_entries",
            "upcoming_radars",
            "bill_reminders",
            "payment_transactions",
            "payment_events",
            "liabilities_vault",
            "loan_payments",
            "loan_prepayments",
            "notifications",
            "audit_logs",
            "outbox_events",
            "alembic_version"
        }

        assert expected_tables.issubset(tables), f"Missing tables in migration: {expected_tables - tables}"

        # Verify partial unique indexes exist
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("payment_transactions")}
        assert "uq_bill_active_payment" in indexes
        assert bool(indexes["uq_bill_active_payment"]["unique"]) is True
        assert "uq_bill_idempotency" in indexes
        assert bool(indexes["uq_bill_idempotency"]["unique"]) is True

        engine.dispose()
    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass
