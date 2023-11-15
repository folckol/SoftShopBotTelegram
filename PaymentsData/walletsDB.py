import asyncio

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime, Float, NullPool
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, relationship, DeclarativeBase
from sqlalchemy.ext.declarative import declarative_base

# Настройка базы данных
engine = create_async_engine('postgresql+asyncpg://postgres:Vanilla9797@localhost/Wallets', poolclass=NullPool)
async_wallet_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass

class Wallet(Base):
    __tablename__ = 'wallets'
    id = Column(String, primary_key=True)

    network = Column(String, nullable=False)
    address = Column(String, nullable=False)
    private_key = Column(String, primary_key=True, nullable=False)
    is_busy = Column(Boolean, default=False)

async def async_main():

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(async_main())