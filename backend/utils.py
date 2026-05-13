import uuid
from bson import ObjectId
from bson.errors import InvalidId


def new_id() -> str:
    """Generate a new UUID string for use as document _id."""
    return str(uuid.uuid4())


async def find_by_id(collection, id_str: str):
    """
    Find a document by string ID with backward compatibility.
    Supports both UUID strings (new records) and ObjectId hex strings (legacy records).
    """
    if not id_str:
        return None
    # Try as plain string first (UUID-based records)
    doc = await collection.find_one({"_id": id_str})
    if doc is None:
        # Fall back to ObjectId for legacy MongoDB-generated _id values
        try:
            doc = await collection.find_one({"_id": ObjectId(id_str)})
        except (InvalidId, Exception):
            pass
    return doc
