from motor.motor_asyncio import AsyncIOMotorClient
import os

_client = None
_db = None


async def init_db():
    global _client, _db
    _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    _db = _client[os.environ["DB_NAME"]]


def get_db():
    return _db
