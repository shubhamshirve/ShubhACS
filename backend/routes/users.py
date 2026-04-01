from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional

from database import get_db
from auth_utils import get_current_user, require_roles, hash_password

router = APIRouter(prefix="/users", tags=["users"])


def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc.pop("password_hash", None)
    return doc


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str  # operator, staff
    operator_id: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    operator_id: Optional[str] = None


class PasswordReset(BaseModel):
    new_password: str


@router.get("")
async def list_users(current_user: dict = Depends(get_current_user)):
    db = get_db()
    query = {}
    if current_user["role"] == "super_admin":
        query = {}
    elif current_user["role"] == "operator":
        query = {"operator_id": current_user["operator_id"]}
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    users = await db.users.find(query).sort("created_at", -1).to_list(500)
    result = []
    for u in users:
        u = serialize(u)
        if u.get("operator_id"):
            op = await db.operators.find_one({"_id": ObjectId(u["operator_id"])})
            u["operator_name"] = op["name"] if op else "Unknown"
        result.append(u)
    return result


@router.post("")
async def create_user(data: UserCreate, current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user["role"] == "super_admin":
        if data.role not in ["super_admin", "operator", "staff"]:
            raise HTTPException(status_code=400, detail="Invalid role")
    elif current_user["role"] == "operator":
        if data.role != "staff":
            raise HTTPException(status_code=403, detail="Operators can only create staff")
        data.operator_id = current_user["operator_id"]
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    email = data.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    doc = {
        "email": email,
        "name": data.name,
        "password_hash": hash_password(data.password),
        "role": data.role,
        "operator_id": data.operator_id,
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user["role"] == "operator" and target.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "email" in update_data:
        update_data["email"] = update_data["email"].lower().strip()
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    return serialize(target)


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    data: PasswordReset,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user["role"] == "operator" and target.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if current_user["role"] == "staff":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    return {"message": "Password reset successfully"}


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    if current_user["role"] not in ["super_admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user["role"] == "operator" and target.get("operator_id") != current_user["operator_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if str(target["_id"]) == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"message": "User deleted"}
