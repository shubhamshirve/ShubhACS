from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import secrets as _secrets

from database import get_db
from auth_utils import get_current_user, require_roles
from utils import find_by_id, new_id
from crypto_utils import encrypt_value, decrypt_value, mask_credential

router = APIRouter(prefix="/operators", tags=["operators"])


def serialize(doc: dict) -> dict:
    """Serialize an operator document for API responses.
    ACS password is masked — use the /acs-credentials endpoint to reveal.
    """
    doc["id"] = str(doc.pop("_id"))
    if "acs_password" in doc:
        doc["acs_password"] = mask_credential(doc["acs_password"])
    return doc


def _gen_password() -> str:
    """Generate a secure 12-char ACS password."""
    return _secrets.token_urlsafe(9)   # ~12 URL-safe chars


class OperatorCreate(BaseModel):
    name: str
    code: str
    contact_email: str
    contact_phone: str = ""
    address: str = ""
    is_active: bool = True
    acs_username: str = ""   # auto-generated from lowercase code if blank
    acs_password: str = ""   # auto-generated random string if blank


class OperatorUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None
    acs_username: Optional[str] = None
    acs_password: Optional[str] = None


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
    # Check code uniqueness
    existing = await db.operators.find_one({"code": data.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Operator code already exists")

    # Derive ACS credentials
    acs_username = (data.acs_username or data.code.lower()).strip().replace(" ", "-")
    acs_password = data.acs_password.strip() or _gen_password()

    # Ensure acs_username is unique
    if await db.operators.find_one({"acs_username": acs_username}):
        raise HTTPException(status_code=400, detail=f"ACS username '{acs_username}' is already in use. Choose a different one.")

    doc = {
        "_id": new_id(),
        "name": data.name,
        "code": data.code.upper(),
        "contact_email": data.contact_email,
        "contact_phone": data.contact_phone,
        "address": data.address,
        "is_active": data.is_active,
        "acs_username": acs_username,
        # Encrypt the ACS password at rest — use /acs-credentials to reveal
        "acs_password": encrypt_value(acs_password),
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.operators.insert_one(doc)
    # Return doc with revealed plaintext for this one creation response only
    serialized = serialize(doc)
    serialized["acs_password_plain"] = acs_password  # shown once on creation
    return serialized


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
    if "acs_username" in update_data:
        acs_username = update_data["acs_username"].strip().replace(" ", "-")
        # Check uniqueness (excluding current operator)
        conflict = await db.operators.find_one({"acs_username": acs_username, "_id": {"$ne": op["_id"]}})
        if conflict:
            raise HTTPException(status_code=400, detail=f"ACS username '{acs_username}' is already in use.")
        update_data["acs_username"] = acs_username
    if "acs_password" in update_data:
        # Encrypt the new password before storing
        update_data["acs_password"] = encrypt_value(update_data["acs_password"])

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


@router.get("/{op_id}/acs-credentials")
async def reveal_acs_credentials(
    op_id: str,
    current_user: dict = Depends(require_roles("super_admin"))
):
    """
    Returns the plaintext ACS username and password for configuring a router's
    CWMP settings.  Restricted to super_admin only.
    """
    db = get_db()
    op = await find_by_id(db.operators, op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operator not found")
    return {
        "operator_id": op_id,
        "operator_name": op["name"],
        "acs_username": op["acs_username"],
        "acs_password": decrypt_value(op["acs_password"]),
    }
