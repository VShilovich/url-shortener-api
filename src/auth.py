from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_async_session
from src.models import User
from src.schemas import UserCreate, UserResponse
from src.config import SECRET_KEY

# настройки для токена
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # пусть живет сутки

# создаем роутер
router = APIRouter(prefix="/auth", tags=["auth"])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    # хэшируем пароль
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    # проверяем, нет ли уже такого email в базе
    query = select(User).where(User.email == user_data.email)
    result = await session.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="такой email уже занят")
    
    # хэшируем пароль и сохраняем юзера
    hashed_pw = get_password_hash(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pw)
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    return new_user

@router.post("/login")
async def login_user(response: Response, user_data: UserCreate, session: AsyncSession = Depends(get_async_session)):
    # ищем юзера
    query = select(User).where(User.email == user_data.email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="неверный email или пароль")

    # генерим токен, зашиваем туда id юзера
    access_token = create_access_token(data={"sub": str(user.id)})
    
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return {"message": "успешный вход"}

@router.post("/logout")
async def logout_user(response: Response):
    response.delete_cookie("access_token")
    return {"message": "вы вышли из аккаунта"}


# зависимости для проверки авторизации
async def get_current_user_optional(request: Request, session: AsyncSession = Depends(get_async_session)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    query = select(User).where(User.id == int(user_id))
    result = await session.execute(query)
    return result.scalar_one_or_none()

# требует авторизацию
async def get_current_user(user: User = Depends(get_current_user_optional)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="вы не авторизованы")
    return user