import asyncio

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime, Float, NullPool
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from sqlalchemy.ext.declarative import declarative_base

# Настройка базы данных
engine = create_async_engine('postgresql+asyncpg://d', poolclass=NullPool)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)

    username = Column(String)
    referrer_id = Column(Integer)
    ref_code = Column(String, default=None)
    ref_count = Column(Integer, default=0)
    ref_rewards = Column(Float, default=0)

    start_date = Column(DateTime)

    purchases = relationship("Soft", backref="user")

class Soft(Base):
    __tablename__ = 'softs'
    id = Column(String, primary_key=True)

    title = Column(String)
    callback_title = Column(String)
    price = Column(Integer)
    description = Column(String)
    upload_date = Column(DateTime)

    user_id = Column(Integer, ForeignKey('users.id'))


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(String, primary_key=True)

    user_id = Column(Integer)


async def async_main():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(async_main())