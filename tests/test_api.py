import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock


async def test_register_and_login(async_client: AsyncClient):
    user_data = {"email": "test@student.com", "password": "password123"}
    
    # регистрация
    resp = await async_client.post("/auth/register", json=user_data)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@student.com"

    # дубликат email должен выдать 400
    resp_dup = await async_client.post("/auth/register", json=user_data)
    assert resp_dup.status_code == 400

    # успешный логин
    login_resp = await async_client.post("/auth/login", json=user_data)
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.cookies

    # неверный пароль
    bad_login = await async_client.post("/auth/login", json={"email": "test@student.com", "password": "wrong"})
    assert bad_login.status_code == 401

    # выход из системы
    logout_resp = await async_client.post("/auth/logout")
    assert logout_resp.status_code == 200


async def test_create_and_redirect_link(async_client: AsyncClient):
    # создаем анонимную ссылку
    resp = await async_client.post("/links/shorten", json={"original_url": "https://python.org"})
    assert resp.status_code == 200
    short_code = resp.json()["short_code"]

    # проверяем редирект
    redir_resp = await async_client.get(f"/links/{short_code}")
    assert redir_resp.status_code == 307
    assert redir_resp.headers["location"] == "https://python.org"

    # проверяем стату
    stats_resp = await async_client.get(f"/links/{short_code}/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["original_url"] == "https://python.org"

async def test_custom_alias_and_search(async_client: AsyncClient):
    # ссылка с кастомным алиасом
    resp = await async_client.post("/links/shorten", json={
        "original_url": "https://yandex.ru",
        "custom_alias": "my-yandex"
    })
    assert resp.status_code == 200
    assert resp.json()["short_code"] == "my-yandex"

    # если алиас занят, должна быть 400
    resp_dup = await async_client.post("/links/shorten", json={
        "original_url": "https://google.com",
        "custom_alias": "my-yandex"
    })
    assert resp_dup.status_code == 400

    # поиск по оригинальному URL
    search_resp = await async_client.get("/links/search?original_url=https://yandex.ru")
    assert search_resp.status_code == 200
    assert len(search_resp.json()) >= 1

async def test_update_and_delete_link(async_client: AsyncClient):
    # регаем юзера и логинимся, чтобы стать владельцем ссылки
    await async_client.post("/auth/register", json={"email": "owner@mail.com", "password": "123"})
    await async_client.post("/auth/login", json={"email": "owner@mail.com", "password": "123"})

    # создаем ссылку от имени залогиненного юзера
    resp = await async_client.post("/links/shorten", json={"original_url": "https://old-site.com"})
    short_code = resp.json()["short_code"]

    # обновляем ссылку
    put_resp = await async_client.put(f"/links/{short_code}", json={"original_url": "https://new-site.com"})
    assert put_resp.status_code == 200
    assert put_resp.json()["original_url"] == "https://new-site.com"

    # удаляем ссылку
    del_resp = await async_client.delete(f"/links/{short_code}")
    assert del_resp.status_code == 200

    # проверяем, что удалилась
    get_del_resp = await async_client.get(f"/links/{short_code}")
    assert get_del_resp.status_code == 404


async def test_expired_and_cleanup(async_client: AsyncClient):
    await async_client.post("/auth/register", json={"email": "cleaner@mail.com", "password": "123"})
    await async_client.post("/auth/login", json={"email": "cleaner@mail.com", "password": "123"})
    
    # создаем заведомо протухшую ссылку
    exp_resp = await async_client.post("/links/shorten", json={
        "original_url": "https://expired.com",
        "expires_at": "2020-01-01T00:00:00"
    })
    short_code = exp_resp.json()["short_code"]

    # при попытке перехода должны получить 410
    redir_resp = await async_client.get(f"/links/{short_code}")
    assert redir_resp.status_code == 410

    # проверяем эндпоинт истории истекших ссылок
    history_resp = await async_client.get("/links/my/expired")
    assert history_resp.status_code == 200
    assert len(history_resp.json()) >= 1

    # дергаем эндпоинт очистки старых ссылок
    cleanup_resp = await async_client.delete("/links/cleanup/unused")
    assert cleanup_resp.status_code == 200
    assert "Очистка завершена" in cleanup_resp.json()["message"]


async def test_cache_hit(async_client: AsyncClient, mocker):
    mocker.patch("src.links.redis_client.get", new_callable=AsyncMock, return_value="https://cached-url.com")
    mocker.patch("src.links.update_click_stats", new_callable=AsyncMock)
    
    resp = await async_client.get("/links/cached_code")
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://cached-url.com"

async def test_404_and_403_errors(async_client: AsyncClient):
    # запрос несуществующей ссылки
    resp_404 = await async_client.get("/links/not_exist")
    assert resp_404.status_code == 404

    # создаем пользователя и ссылку
    await async_client.post("/auth/register", json={"email": "user1@mail.com", "password": "123"})
    await async_client.post("/auth/login", json={"email": "user1@mail.com", "password": "123"})
    resp = await async_client.post("/links/shorten", json={"original_url": "https://site.com"})
    short_code = resp.json()["short_code"]

    # регистрируем второго пользователя
    await async_client.post("/auth/register", json={"email": "hacker@mail.com", "password": "123"})
    await async_client.post("/auth/login", json={"email": "hacker@mail.com", "password": "123"})

    # этот пользователь пытается удалить или изменить чужую ссылку
    del_resp = await async_client.delete(f"/links/{short_code}")
    assert del_resp.status_code == 403

    put_resp = await async_client.put(f"/links/{short_code}", json={"original_url": "https://hacked.com"})
    assert put_resp.status_code == 403

    # пытается обновить несуществующую ссылку
    bad_put = await async_client.put("/links/fake_code", json={"original_url": "https://fake.com"})
    assert bad_put.status_code == 404

async def test_main_endpoints_and_bad_token(async_client: AsyncClient):
    # проверяем тестовые эндпоинты из мейна
    resp1 = await async_client.get("/maybe_me")
    assert resp1.status_code == 200

    # подсовываем фальшивый токен
    async_client.cookies.set("access_token", "fake.jwt.token")
    resp2 = await async_client.get("/me")
    assert resp2.status_code == 401