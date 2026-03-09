from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # один ко многим
    links = relationship("Link", back_populates="owner", cascade="all, delete-orphan")

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    
    # время создания и время протухания
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP, nullable=True)
    
    # статистика
    clicks = Column(Integer, default=0)
    last_used_at = Column(TIMESTAMP, nullable=True)
    
    # флаг активности
    is_active = Column(Boolean, default=True)

    # привязка к автору
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    owner = relationship("User", back_populates="links")