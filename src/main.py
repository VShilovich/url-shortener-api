from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as aioredis
import uvicorn

from src.auth import router as auth_router, get_current_user, get_current_user_optional
from src.links import router as links_router
from src.models import User

# lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = aioredis.from_url("redis://redis:6379")
    
    # инициализируем кэш
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    
    yield
    
    await redis_client.close()

app = FastAPI(title="URL Shortener API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(links_router)

# тестовые эндпоинты
@app.get("/me")
async def get_my_info(user: User = Depends(get_current_user)):
    return {"email": user.email, "id": user.id}

@app.get("/maybe_me")
async def get_optional_info(user: User = Depends(get_current_user_optional)):
    if user:
        return {"status": "залогинен", "email": user.email}
    return {"status": "аноним"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)