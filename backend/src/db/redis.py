import redis.asyncio as aioredis

from src.config import Config

JTI_EXPIRY = 3600

token_blocklist = aioredis.from_url(Config.REDIS_URL, decode_responses=True)
# token_blocklist = aioredis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


async def add_jti_to_blocklist(jti: str) -> None:
    # print(f"Adding JTI to blocklist: {jti}")
    await token_blocklist.set(name=jti, value="", ex=JTI_EXPIRY)


async def token_in_blocklist(jti: str) -> bool:
    jti = await token_blocklist.get(jti)

    return jti is not None
