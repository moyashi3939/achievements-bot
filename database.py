# database.py
import asyncpg

async def create_db_pool(uri: str):
    return await asyncpg.create_pool(uri)