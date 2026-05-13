from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from database import get_db
from auth_utils import get_current_user, require_roles
from utils import find_by_id, new_id

router = APIRouter(prefix="/operators", tags=["operators"])


def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


class OperatorCreate(BaseModel):
    name: str
    code: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    is_active: bool = True


class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("")
async def list_operators(current_user: dict = Depends(require_roles("super_admin"))):
    db = get_db()
    ops = await db.operators.find({}).sort("name", 1).to_list(500)
    result = []
    for op in ops:
        op = serialize(op)
        op["device_count"] = await db.devices.count_documents({"operator_id": op["id"]})
        op["staff_count"] = await db.users.count_documents({"operator_id": op["id"]})
        result.append(op)
    return result


@router.get("/{op_id}")
async def get_operator(op_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user["role"] not in ["super_admin"] and current_user.get("operator_id") != op_id:
        raise HTTPException(status_code=403, detail="Access denied")
    op = await find_by_id(db.operators, op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    return serialize(op)


@router.post("")
async def create_operator(
    data: OperatorCreate,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    existing = await db.operators.find_one({"code": data.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Operator code already exists")
    doc = {
        "_id": new_id(),
        **data.model_dump(),
        "code": data.code.upper(),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.operators.insert_one(doc)
    return serialize(doc)


@router.put("/{op_id}")
async def update_operator(
    op_id: str,
    data: OperatorUpdate,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    op = await find_by_id(db.operators, op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "code" in update_data:
        update_data["code"] = update_data["code"].upper()
    await db.operators.update_one({"_id": op["_id"]}, {"$set": update_data})
    op = await find_by_id(db.operators, op_id)
    return serialize(op)


@router.delete("/{op_id}")
async def delete_operator(
    op_id: str,
    current_user: dict = Depends(require_roles("super_admin"))
):
    db = get_db()
    op = await find_by_id(db.operators, op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    device_count = await db.devices.count_documents({"operator_id": op_id})
    if device_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete operator with {device_count} devices. Remove devices first."
        )
    await db.users.delete_many({"operator_id": op_id})
    await db.operators.delete_one({"_id": op["_id"]})
    return {"message": "Operator deleted"}
