from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timezone
import jwt

from database import get_db
from auth_utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    set_auth_cookies, get_current_user, get_jwt_secret, JWT_ALGORITHM
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    db = get_db()
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")

    user_id = str(user["_id"])
    operator_id = user.get("operator_id")
    access_token = create_access_token(user_id, email, user["role"], operator_id)
    refresh_token = create_refresh_token(user_id)
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "id": user_id,
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "operator_id": operator_id,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    db = get_db()
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = str(user["_id"])
        access_token = create_access_token(
            user_id, user["email"], user["role"], user.get("operator_id")
        )
        response.set_cookie(
            "access_token", access_token, httponly=True,
            secure=False, samesite="lax", max_age=28800, path="/"
        )
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(current_user["_id"] if "_id" in current_user else current_user["id"])})
    uid = current_user.get("id") or current_user.get("_id")
    user = await db.users.find_one({"_id": ObjectId(uid)})
    if not user or not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one(
        {"_id": ObjectId(uid)},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    return {"message": "Password updated successfully"}
