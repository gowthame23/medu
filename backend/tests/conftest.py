import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool, NullPool

from app.main import app
from app.core.database import get_db
from app.models.base import Base
import app.models as _models  # Ensure all model tables are registered with Base.metadata
from app.models.user import User
from app.core.security import hash_password, create_access_token
import os
from app.repositories.expense import ExpenseRepository

# Support real Postgres via DATABASE_URL or TEST_DATABASE_URL, with in-memory SQLite fallback
TEST_DB_ENV = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

if TEST_DB_ENV and not TEST_DB_ENV.startswith("sqlite"):
    if TEST_DB_ENV.startswith("postgresql://"):
        TEST_DB_ENV = TEST_DB_ENV.replace("postgresql://", "postgresql+asyncpg://", 1)
    test_async_engine = create_async_engine(
        TEST_DB_ENV,
        poolclass=NullPool,
        echo=False,
        future=True
    )
else:
    TEST_DATABASE_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"
    test_async_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=NullPool,
        echo=False,
        future=True
    )

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def keep_alive_sqlite():
    if not (TEST_DB_ENV and not TEST_DB_ENV.startswith("sqlite")):
        conn = await test_async_engine.connect()
        yield conn
        await conn.close()
    else:
        yield None


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        repo = ExpenseRepository(session)
        await repo.seed_system_categories()

    yield

    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def create_user_fixture():
    async def _create(email: str, display_name: str, password: str = "SecurePass123!") -> tuple[User, str]:
        async with TestAsyncSessionLocal() as session:
            user = User(
                email=email.lower(),
                password_hash=hash_password(password),
                display_name=display_name,
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            token = create_access_token(str(user.id), user.email)
            return user, token
    return _create
