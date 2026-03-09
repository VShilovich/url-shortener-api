import os
from dotenv import load_dotenv

# грузим переменные из .env файла
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret")

# лимит дней для удаления неиспользуемых ссылок
UNUSED_DAYS_LIMIT = int(os.getenv("UNUSED_DAYS_LIMIT", 30))