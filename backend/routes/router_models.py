from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List

from database import get_db
from auth_utils import get_current_user, require_roles
from utils import find_by_id, new_id

router = APIRouter(prefix="/router-models", tags=["router-models"])


def serialize(doc: dict) -> dict:
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


class RouterModelCreate(BaseModel):
    brand: str
    model: str
    isps: List[str] = []
    protocols: List[str] = ["TR-069"]
    chipset: str = ""
    category: str = ""
    ports: dict = {}
    notes: str = ""
    is_active: bool = True


class RouterModelUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    isps: Optional[List[str]] = None
    protocols: Optional[List[str]] = None
    chipset: Optional[str] = None
    category: Optional[str] = None
    ports: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_router_models(
    search: Optional[str] = None,
    isp: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    query = {}
    if search:
        query["$or"] = [
            {"brand": {"$regex": search, "$options": "i"}},
            {"model": {"$regex": search, "$options": "i"}},
            {"chipset": {"$regex": search, "$options": "i"}},
        ]
    if isp:
        query["isps"] = {"$in": [isp]}
    models = await db.router_models.find(query).sort("brand", 1).to_list(500)
    return [serialize(m) for m in models]


@router.post("")
async def create_router_model(
    data: RouterModelCreate,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    doc = {
        "_id": new_id(),
        **data.model_dump(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.router_models.insert_one(doc)
    return serialize(doc)


@router.put("/{model_id}")
async def update_router_model(
    model_id: str,
    data: RouterModelUpdate,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    model = await find_by_id(db.router_models, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Router model not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.router_models.update_one({"_id": model["_id"]}, {"$set": update_data})
    model = await find_by_id(db.router_models, model_id)
    return serialize(model)


@router.delete("/{model_id}")
async def delete_router_model(
    model_id: str,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    model = await find_by_id(db.router_models, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Router model not found")
    await db.router_models.delete_one({"_id": model["_id"]})
    return {"message": "Router model deleted"}
