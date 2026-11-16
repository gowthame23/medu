import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import AsyncSessionLocal
from app.jobs.reconciliation import reconcile_stale_pending_payments
from app.jobs.outbox_publisher import publish_pending_outbox_events

scheduler = AsyncIOScheduler()


async def scheduled_payment_reconciliation_job():
    async with AsyncSessionLocal() as session:
        await reconcile_stale_pending_payments(session)


async def scheduled_outbox_publisher_job():
    async with AsyncSessionLocal() as session:
        await publish_pending_outbox_events(session)


def start_scheduler():
    scheduler.add_job(
        scheduled_payment_reconciliation_job,
        "interval",
        minutes=5,
        id="payment_reconciliation",
        replace_existing=True
    )
    scheduler.add_job(
        scheduled_outbox_publisher_job,
        "interval",
        seconds=15,
        id="outbox_publisher",
        replace_existing=True
    )
    scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
