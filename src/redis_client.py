import redis.asyncio as redis
from src.config import REDIS_HOST, REDIS_PORT

# создаем глобальный клиент для работы с кэшем
redis_client = redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)