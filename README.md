# URL Shortener API

Сервис для сокращения длинных ссылок с поддержкой авторизации, аналитикой, кешированием и автоматической очисткой данных.

## Основной функционал
- **Авторизация:** JWT-аутентификация с хранением токенов.
- **Управление ссылками:** Создание (с кастомным алиасом и временем жизни `expires_at`), удаление, обновление.
- **Редирект:** Быстрый переход по короткой ссылке с использованием **Redis** для кеширования.
- **Статистика:** Учет кликов и даты последнего использования.
- **Фоновые задачи:** Использование `BackgroundTasks` для обновления статистики.
- **Дополнительно:** Поиск по оригинальному URL, просмотр истории истечения ссылок, ручная очистка неиспользуемых ссылок.

## Стек технологий
- **Backend:** FastAPI
- **DB:** PostgreSQL (SQLAlchemy 2.0 + asyncpg)
- **Cache:** Redis
- **Containerization:** Docker & Docker Compose
- **Auth:** JWT, BCrypt

## Установка и запуск

1. **Клонирование репозитория:**
```bash
git clone https://github.com/VShilovich/url-shortener-api.git
cd url_shortener
```

2. **Настройка переменных окружения:**
Создайте файл `.env` в корне проекта:
```env
DB_USER=postgres
DB_PASS=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=shortener_db
REDIS_HOST=redis
REDIS_PORT=6379
SECRET_KEY=очень_секретная_строка
UNUSED_DAYS_LIMIT=30
```

3. **Запуск:**
```bash
docker compose up --build
```
После запуска API будет доступно по адресу `http://localhost:8000/docs`.

## Описание API

### Аутентификация
- `POST /auth/register` — Регистрация пользователя.
- `POST /auth/login` — Вход в систему.
- `POST /auth/logout` — Выход.

### Ссылки
- `POST /links/shorten` — Создать короткую ссылку.
- `GET /links/{short_code}` — Переход по ссылке (редирект).
- `DELETE /links/{short_code}` — Удаление ссылки (требуется авторизация).
- `PUT /links/{short_code}` — Обновление оригинального URL (требуется авторизация).
- `GET /links/{short_code}/stats` — Получение статистики.
- `GET /links/search` — Поиск ссылок по оригинальному URL.
- `GET /links/my/expired` — Получение списка истекших/неактивных ссылок.
- `DELETE /links/cleanup/unused` — Очистка ссылок, не использовавшихся дольше N дней.

4. **Миграции базы данных:**
   Если таблицы не создались автоматически, выполните миграции вручную:

```
bash
   docker exec -it shortener_app alembic upgrade head