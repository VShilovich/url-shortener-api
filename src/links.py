import string
import random
from datetime import datetime, timedelta
from src.config import UNUSED_DAYS_LIMIT
from typing import List
from fastapi import BackgroundTasks
from src.redis_client import redis_client
from src.database import async_session_maker
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_async_session
from src.models import Link, User
from src.schemas import LinkCreate, LinkUpdate, LinkResponse
from src.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/links", tags=["links"])

# функция для генерации случайного кода
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@router.post("/shorten", response_model=LinkResponse)
async def shorten_url(
    link_data: LinkCreate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user_optional)
):
    # если пользователь захотел свой собственный алиас
    if link_data.custom_alias:
        query = select(Link).where(Link.short_code == link_data.custom_alias)
        res = await session.execute(query)
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="этот alias уже занят, придумайте другой")
        short_code = link_data.custom_alias
    else:
        # генерим рандомный код и проверяем, вдруг такой уже есть в базе
        while True:
            short_code = generate_short_code()
            query = select(Link).where(Link.short_code == short_code)
            res = await session.execute(query)
            if not res.scalar_one_or_none():
                break

    expires_at = link_data.expires_at
    if expires_at and expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)

    # создаем новую ссылку
    new_link = Link(
        original_url=link_data.original_url,
        short_code=short_code,
        expires_at=expires_at,
        user_id=user.id if user else None
    )
    
    session.add(new_link)
    await session.commit()
    await session.refresh(new_link)
    
    return new_link

# фоновая задача для накрутки счетчика, если мы достали ссылку из кэша
async def update_click_stats(short_code: str):
    async with async_session_maker() as session:
        query = select(Link).where(Link.short_code == short_code)
        res = await session.execute(query)
        db_link = res.scalar_one_or_none()
        
        if db_link:
            db_link.clicks += 1
            db_link.last_used_at = datetime.utcnow()
            await session.commit()

@router.get("/search", response_model=List[LinkResponse])
async def search_links(
    original_url: str,
    session: AsyncSession = Depends(get_async_session)
):
    # ищем все короткие ссылки
    query = select(Link).where(Link.original_url == original_url)
    res = await session.execute(query)
    links = res.scalars().all()
    
    return links

@router.get("/{short_code}/stats", response_model=LinkResponse)
async def get_link_stats(
    short_code: str,
    session: AsyncSession = Depends(get_async_session)
):
    # достаем ссылку из базы
    query = select(Link).where(Link.short_code == short_code)
    res = await session.execute(query)
    db_link = res.scalar_one_or_none()

    if not db_link:
        raise HTTPException(status_code=404, detail="ссылка не найдена")

    return db_link


@router.get("/my/expired", response_model=List[LinkResponse])
async def get_my_expired_links(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user) 
):
    # ищем ссылки текущего юзера, которые либо помечены как неактивные, 
    # либо их срок годности уже вышел
    query = select(Link).where(
        Link.user_id == user.id,
        (Link.is_active == False) | (Link.expires_at < datetime.utcnow())
    )
    res = await session.execute(query)
    expired_links = res.scalars().all()
    
    return expired_links

@router.delete("/cleanup/unused")
async def cleanup_unused_links(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)
):
    threshold_date = datetime.utcnow() - timedelta(days=UNUSED_DAYS_LIMIT)
    
    # ищем ссылки, у которых был переход, но очень давно или переходов вообще не было,
    # и созданы они давно 
    query = select(Link).where(
        (Link.last_used_at < threshold_date) | 
        ((Link.last_used_at == None) & (Link.created_at < threshold_date))
    )
    res = await session.execute(query)
    links_to_delete = res.scalars().all()

    count = 0
    for link in links_to_delete:
        await redis_client.delete(link.short_code)
        await session.delete(link)
        count += 1

    await session.commit()
    return {"message": f"Очистка завершена. Удалено старых ссылок: {count}"}

@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    cached_url = await redis_client.get(short_code)
    if cached_url:
        background_tasks.add_task(update_click_stats, short_code)
        return RedirectResponse(url=cached_url, status_code=307)

    query = select(Link).where(Link.short_code == short_code)
    res = await session.execute(query)
    db_link = res.scalar_one_or_none()

    if not db_link or not db_link.is_active:
        raise HTTPException(status_code=404, detail="ссылка не найдена или удалена")

    # проверяем срок годности
    if db_link.expires_at and db_link.expires_at < datetime.utcnow():
        db_link.is_active = False
        await session.commit()
        await redis_client.delete(short_code)
        raise HTTPException(status_code=410, detail="срок действия ссылки истек")

    await redis_client.set(short_code, db_link.original_url, ex=3600)

    # обновляем стату сразу синхронно
    db_link.clicks += 1
    db_link.last_used_at = datetime.utcnow()
    await session.commit()

    return RedirectResponse(url=db_link.original_url, status_code=307)

@router.delete("/{short_code}")
async def delete_link(
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user)
):
    query = select(Link).where(Link.short_code == short_code)
    res = await session.execute(query)
    db_link = res.scalar_one_or_none()

    if not db_link:
        raise HTTPException(status_code=404, detail="ссылка не найдена")
    
    # проверяем, что удаляет именно владелец
    if db_link.user_id != user.id:
        raise HTTPException(status_code=403, detail="вы не можете удалить чужую ссылку")

    await session.delete(db_link)
    await session.commit()
    await redis_client.delete(short_code)
    return {"message": "ссылка успешно удалена"}

@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    link_data: LinkUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user) 
):
    query = select(Link).where(Link.short_code == short_code)
    res = await session.execute(query)
    db_link = res.scalar_one_or_none()

    if not db_link:
        raise HTTPException(status_code=404, detail="ссылка не найдена")
    
    # проверка прав
    if db_link.user_id != user.id:
        raise HTTPException(status_code=403, detail="вы не можете изменить чужую ссылку")

    db_link.original_url = link_data.original_url
    await session.commit()
    await session.refresh(db_link)
    await redis_client.delete(short_code)
    
    return db_link