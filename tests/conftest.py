import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock

from src.main import app
from src.database import get_async_session
from src.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# создаем тестовый движок
test_engine = create_async_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

# подменяем реальную базу на тестовую
async def override_get_async_session():
    async with test_session_maker() as session:
        yield session

app.dependency_overrides[get_async_session] = override_get_async_session


# фикстура для создания и удаления таблиц перед/после каждого теста
@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# фикстура для асинхронных http запросов
@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

# мокаем редис, чтобы тесты вообще не зависели от докера и сети
@pytest.fixture(autouse=True)
def mock_redis(mocker):
    mocker.patch("src.links.redis_client.get", new_callable=AsyncMock, return_value=None)
    mocker.patch("src.links.redis_client.set", new_callable=AsyncMock)
    mocker.patch("src.links.redis_client.delete", new_callable=AsyncMock)