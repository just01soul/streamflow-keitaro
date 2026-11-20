import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        host="localhost",
        port=5432,
        database="streamflow",
    )
    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    tables = [r["tablename"] for r in rows]
    print("Таблицы:", tables)
    await conn.close()


asyncio.run(main())