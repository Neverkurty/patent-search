import asyncio
import asyncpg


async def main() -> None:
    conn = await asyncpg.connect(
        "postgresql://paten:paten@127.0.0.1:5433/paten"
    )
    val = await conn.fetchval("SELECT 1")
    print("ok", val)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
