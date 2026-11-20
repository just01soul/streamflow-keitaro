import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        host="localhost",
        port=5432,
        database="postgres",
    )
    try:
        await conn.execute("CREATE DATABASE streamflow")
        print("База streamflow создана")
    except asyncpg.exceptions.DuplicateDatabaseError:
        print("База streamflow уже существует")
    finally:
        await conn.close()

asyncio.run(main())