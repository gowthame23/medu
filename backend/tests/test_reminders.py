import re
import zoneinfo
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.notification import Notification
from app.models.expense import DailyLog, DailyLogEntry, ExpenseCategory
from app.jobs.reminders import (
    process_daily_reminders,
    resolve_user_timezone,
    MORNING_MESSAGE,
    EVENING_MESSAGE,
    MORNING_TITLE,
    EVENING_TITLE,
)
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_both_slots_fire_at_right_local_time(db_session: AsyncSession):
    """
    Asserts both 10:00 morning and 18:00 evening slots fire at the exact local time:
    - Before 10:00 local: 0 reminders
    - At/after 10:00 local: morning fires, evening does not
    - At/after 18:00 local: evening fires
    """
    user = User(
        email="slots_test@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Slots Tester",
        timezone="Asia/Kolkata",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 1. At 09:59 IST (04:29 UTC on 2026-11-20): neither slot has passed
    t1 = datetime(2026, 11, 20, 4, 29, 0, tzinfo=timezone.utc)
    c1 = await process_daily_reminders(db_session, now_utc=t1)
    assert c1 == 0

    notifs1 = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(notifs1) == 0

    # 2. At 10:00 IST (04:30 UTC on 2026-11-20): morning slot fires
    t2 = datetime(2026, 11, 20, 4, 30, 0, tzinfo=timezone.utc)
    c2 = await process_daily_reminders(db_session, now_utc=t2)
    assert c2 == 1

    notifs2 = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(notifs2) == 1
    assert notifs2[0].type == "REMINDER"
    assert notifs2[0].title == MORNING_TITLE
    assert notifs2[0].message == MORNING_MESSAGE
    assert notifs2[0].dedupe_key == "reminder:morning:2026-11-20"

    # 3. At 17:59 IST (12:29 UTC on 2026-11-20): morning already exists, evening not yet
    t3 = datetime(2026, 11, 20, 12, 29, 0, tzinfo=timezone.utc)
    c3 = await process_daily_reminders(db_session, now_utc=t3)
    assert c3 == 0

    # 4. At 18:00 IST (12:30 UTC on 2026-11-20): evening slot fires
    t4 = datetime(2026, 11, 20, 12, 30, 0, tzinfo=timezone.utc)
    c4 = await process_daily_reminders(db_session, now_utc=t4)
    assert c4 == 1

    notifs4 = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.asc())
    )).scalars().all()
    assert len(notifs4) == 2
    assert notifs4[1].type == "REMINDER"
    assert notifs4[1].title == EVENING_TITLE
    assert notifs4[1].message == EVENING_MESSAGE
    assert notifs4[1].dedupe_key == "reminder:evening:2026-11-20"


@pytest.mark.asyncio
async def test_two_different_timezones(db_session: AsyncSession):
    """
    Asserts reminders fire in each user's own timezone:
    User A in Asia/Tokyo (UTC+9) vs User B in America/New_York (UTC-5).
    At UTC 01:30: Tokyo is 10:30 (morning fires), New York is 20:30 previous day (does not fire for today).
    """
    tokyo_user = User(
        email="tokyo_user@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Tokyo User",
        timezone="Asia/Tokyo",
        is_active=True,
    )
    ny_user = User(
        email="ny_user@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="NY User",
        timezone="America/New_York",
        is_active=True,
    )
    db_session.add_all([tokyo_user, ny_user])
    await db_session.commit()

    # UTC 2026-11-20 01:30:00:
    # Tokyo local: 2026-11-20 10:30:00 (Morning slot passed!)
    # New York local: 2026-11-19 20:30:00 (Previous date!)
    t1 = datetime(2026, 11, 20, 1, 30, 0, tzinfo=timezone.utc)
    await process_daily_reminders(db_session, now_utc=t1)

    tokyo_notifs = (await db_session.execute(
        select(Notification).where(Notification.user_id == tokyo_user.id)
    )).scalars().all()
    assert len(tokyo_notifs) == 1
    assert tokyo_notifs[0].dedupe_key == "reminder:morning:2026-11-20"

    ny_notifs = (await db_session.execute(
        select(Notification).where(
            Notification.user_id == ny_user.id,
            Notification.dedupe_key == "reminder:morning:2026-11-20"
        )
    )).scalars().all()
    assert len(ny_notifs) == 0

    # UTC 2026-11-20 15:30:00:
    # New York local: 2026-11-20 10:30:00 (Morning slot passed for NY!)
    t2 = datetime(2026, 11, 20, 15, 30, 0, tzinfo=timezone.utc)
    await process_daily_reminders(db_session, now_utc=t2)

    ny_notifs_after = (await db_session.execute(
        select(Notification).where(
            Notification.user_id == ny_user.id,
            Notification.dedupe_key == "reminder:morning:2026-11-20"
        )
    )).scalars().all()
    assert len(ny_notifs_after) == 1


@pytest.mark.asyncio
async def test_dst_transition_day(db_session: AsyncSession):
    """
    Asserts correct behavior across a Daylight Saving Time (DST) transition date:
    In America/New_York, DST ends on Sunday 2026-11-01 at 02:00 EDT -> 01:00 EST (UTC-5).
    - 14:00 UTC on 2026-11-01 is 09:00 EST (before 10:00 -> morning slot must NOT fire).
    - 15:00 UTC on 2026-11-01 is exactly 10:00 EST (morning slot fires).
    - 23:00 UTC on 2026-11-01 is exactly 18:00 EST (evening slot fires).
    """
    user = User(
        email="dst_user@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="DST User",
        timezone="America/New_York",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 1. At 14:00 UTC on 2026-11-01: local time is 09:00 EST -> should not fire
    t1 = datetime(2026, 11, 1, 14, 0, 0, tzinfo=timezone.utc)
    await process_daily_reminders(db_session, now_utc=t1)
    notifs1 = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(notifs1) == 0

    # 2. At 15:00 UTC on 2026-11-01: local time is 10:00 EST -> morning slot fires
    t2 = datetime(2026, 11, 1, 15, 0, 0, tzinfo=timezone.utc)
    await process_daily_reminders(db_session, now_utc=t2)
    notifs2 = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(notifs2) == 1
    assert notifs2[0].dedupe_key == "reminder:morning:2026-11-01"

    # 3. At 23:00 UTC on 2026-11-01: local time is 18:00 EST -> evening slot fires
    t3 = datetime(2026, 11, 1, 23, 0, 0, tzinfo=timezone.utc)
    await process_daily_reminders(db_session, now_utc=t3)
    notifs3 = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(notifs3) == 2
    assert notifs3[1].dedupe_key == "reminder:evening:2026-11-01"


@pytest.mark.asyncio
async def test_duplicate_run_creates_one_row(db_session: AsyncSession):
    """
    Asserts idempotency: running the scheduler job twice for the same slot
    creates exactly ONE notification row in the database.
    """
    user = User(
        email="dedupe_user@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Dedupe User",
        timezone="Asia/Kolkata",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    t = datetime(2026, 11, 20, 13, 0, 0, tzinfo=timezone.utc)  # 18:30 IST

    # First run creates morning + evening
    c1 = await process_daily_reminders(db_session, now_utc=t)
    assert c1 == 2

    # Second run creates 0
    c2 = await process_daily_reminders(db_session, now_utc=t)
    assert c2 == 0

    # Third run creates 0
    c3 = await process_daily_reminders(db_session, now_utc=t)
    assert c3 == 0

    rows = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(rows) == 2
    dedupe_keys = [r.dedupe_key for r in rows]
    assert dedupe_keys == ["reminder:morning:2026-11-20", "reminder:evening:2026-11-20"]


@pytest.mark.asyncio
async def test_evening_reminder_skipped_after_log(db_session: AsyncSession):
    """
    Asserts the evening reminder is skipped if the user already submitted today's daily log.
    """
    user_unlogged = User(
        email="unlogged_user@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Unlogged User",
        timezone="Asia/Kolkata",
        is_active=True,
    )
    user_logged = User(
        email="logged_user@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Logged User",
        timezone="Asia/Kolkata",
        is_active=True,
    )
    db_session.add_all([user_unlogged, user_logged])
    await db_session.commit()

    # User B logs today's spending
    cat_query = select(ExpenseCategory).limit(1)
    cat = (await db_session.execute(cat_query)).scalar_one()

    log_date = datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc).astimezone(
        zoneinfo.ZoneInfo("Asia/Kolkata")
    ).date()

    daily_log = DailyLog(user_id=user_logged.id, log_date=log_date)
    db_session.add(daily_log)
    await db_session.flush()

    entry = DailyLogEntry(
        daily_log_id=daily_log.id,
        category_id=cat.id,
        amount=Decimal("150.00")
    )
    db_session.add(entry)
    await db_session.commit()

    # Run scheduler at 18:30 IST (13:00 UTC)
    t = datetime(2026, 11, 20, 13, 0, 0, tzinfo=timezone.utc)
    await process_daily_reminders(db_session, now_utc=t)

    # User A (unlogged) should have evening reminder
    unlogged_evening = (await db_session.execute(
        select(Notification).where(
            Notification.user_id == user_unlogged.id,
            Notification.dedupe_key == f"reminder:evening:{log_date.isoformat()}"
        )
    )).scalar_one_or_none()
    assert unlogged_evening is not None

    # User B (already logged) must NOT have evening reminder
    logged_evening = (await db_session.execute(
        select(Notification).where(
            Notification.user_id == user_logged.id,
            Notification.dedupe_key == f"reminder:evening:{log_date.isoformat()}"
        )
    )).scalar_one_or_none()
    assert logged_evening is None


@pytest.mark.asyncio
async def test_disabled_settings_skip_reminders(db_session: AsyncSession):
    """
    Asserts reminder is skipped if the user disabled morning or evening reminder settings.
    """
    user_no_morning = User(
        email="no_morning@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="No Morning",
        timezone="Asia/Kolkata",
        reminder_morning_enabled=False,
        reminder_evening_enabled=True,
        is_active=True,
    )
    user_no_evening = User(
        email="no_evening@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="No Evening",
        timezone="Asia/Kolkata",
        reminder_morning_enabled=True,
        reminder_evening_enabled=False,
        is_active=True,
    )
    db_session.add_all([user_no_morning, user_no_evening])
    await db_session.commit()

    t = datetime(2026, 11, 20, 13, 0, 0, tzinfo=timezone.utc)  # 18:30 IST

    await process_daily_reminders(db_session, now_utc=t)

    notifs_no_morning = (await db_session.execute(
        select(Notification).where(Notification.user_id == user_no_morning.id)
    )).scalars().all()
    # Only evening reminder created
    assert len(notifs_no_morning) == 1
    assert notifs_no_morning[0].dedupe_key == "reminder:evening:2026-11-20"

    notifs_no_evening = (await db_session.execute(
        select(Notification).where(Notification.user_id == user_no_evening.id)
    )).scalars().all()
    # Only morning reminder created
    assert len(notifs_no_evening) == 1
    assert notifs_no_evening[0].dedupe_key == "reminder:morning:2026-11-20"


@pytest.mark.asyncio
async def test_invalid_timezone_fallback(db_session: AsyncSession):
    """
    Asserts that an invalid timezone string safely falls back to Asia/Kolkata without raising an error.
    """
    user = User(
        email="bad_tz@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Bad Timezone User",
        timezone="Invalid/Nonexistent_Timezone_12345",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # resolve_user_timezone directly
    tz = resolve_user_timezone(user.timezone)
    assert str(tz) == "Asia/Kolkata"

    # process_daily_reminders handles it gracefully
    t = datetime(2026, 11, 20, 4, 45, 0, tzinfo=timezone.utc)  # 10:15 IST
    created = await process_daily_reminders(db_session, now_utc=t)
    assert created >= 1

    notif = (await db_session.execute(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.dedupe_key == "reminder:morning:2026-11-20"
        )
    )).scalar_one_or_none()
    assert notif is not None
    assert notif.title == MORNING_TITLE
    assert notif.message == MORNING_MESSAGE


@pytest.mark.asyncio
async def test_no_amounts_or_loan_info_in_reminder_text(db_session: AsyncSession):
    """
    Asserts privacy rule: reminder text must contain NO amounts, currency symbols,
    loan, EMI, debt, or liability information.
    """
    user = User(
        email="privacy_check@example.com",
        password_hash=hash_password("SecurePass123!"),
        display_name="Privacy User",
        timezone="Asia/Kolkata",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    t = datetime(2026, 11, 20, 13, 0, 0, tzinfo=timezone.utc)  # 18:30 IST
    await process_daily_reminders(db_session, now_utc=t)

    reminders = (await db_session.execute(
        select(Notification).where(Notification.user_id == user.id)
    )).scalars().all()
    assert len(reminders) == 2

    forbidden_currencies = ["₹", "$", "€", "£", "INR", "USD", "EUR", "rupee", "dollar"]
    forbidden_loan_terms = ["loan", "liability", "liabilities", "mortgage", "emi", "interest", "debt", "principal"]
    amount_pattern = re.compile(r"\b\d+([.,]\d{2})?\b")

    for rem in reminders:
        text = f"{rem.title} {rem.message}".lower()

        # No currency symbols
        for curr in forbidden_currencies:
            assert curr.lower() not in text, f"Found currency '{curr}' in reminder text: '{rem.message}'"

        # No loan / debt / liability terms
        for term in forbidden_loan_terms:
            assert term not in text, f"Found liability term '{term}' in reminder text: '{rem.message}'"

        # No money amounts (e.g. 1500.00, ₹500, etc.)
        assert "₹" not in rem.message
        assert "$" not in rem.message

        # Assert exact pre-approved anxiety-free copy
        if rem.dedupe_key.startswith("reminder:morning"):
            assert rem.message == "Plan your day: check Tomorrow's Radar and list what is due."
        elif rem.dedupe_key.startswith("reminder:evening"):
            assert rem.message == "Time for your 30-second check-in: log today's spending."
