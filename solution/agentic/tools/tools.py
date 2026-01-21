from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

def _project_root()-> Path:
    return Path(__file__).resolve().parents[2]

def _resolve_first_existing(candidates: List[Path])-> Path:
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

def _cultpass_db_path()-> Path:
    root= _project_root()
    return _resolve_first_existing([root / "data" / "external" / "cultpass.db",
                                    root.parent / "data" / "core" / "cultpass_articles.jsonl"
                                    ])

@lru_cache(maxsize= 4)
def _engine(sqlite_path: str)-> Engine:
    return create_engine(f"sqlite:///{sqlite_path}", echo= False, future= True)

def _fetch_one(engine: Engine, sql: str, params: Dict[str, Any])-> Optional[Dict[str, Any]]:
    with engine.connect() as conn:
        row= conn.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

def _fetch_all(engine: Engine, sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]

class ToolError(BaseModel):
    ok : bool= Field(default=False)
    error: str
    details: Optional[Dict[str, Any]]= None

class AccountLookupInput(BaseModel):
    email: str= Field(..., description= "User email to lookup")

class AccountLookupOutput(BaseModel):
    ok: bool= True
    found: bool
    user_id: Optional[str]= None
    full_name: Optional[str]= None
    email: Optional[str]= None
    is_blocked: Optional[bool]= None

class SubscriptionStatusInput(BaseModel):
    user_id: Optional[str] = Field(default=None, description="CultPass user_id.")
    email: Optional[str] = Field(default=None, description="Email (fallback if no user_id).")

class SubscriptionStatusOutput(BaseModel):
    ok: bool = True
    found: bool
    user_id: Optional[str] = None
    active_subscription: bool = False
    plan: Optional[str] = None
    status: Optional[str] = None
    renewal_date: Optional[str] = None

class ReservationLookupInput(BaseModel):
    user_id: str= Field(..., description= "CultPass user_id to list reservations for")
    limit: int= Field(default=5, ge= 1, le= 50)

class ReservationLookupOutput(BaseModel):
    ok: bool = True
    user_id: str
    reservations: List[Dict[str, Any]]

class RetrieveKnowledgeInput(BaseModel):
    query: str = Field(..., description="User question or ticket text.")
    k: int = Field(default=4, ge=1, le=10)

class KnowledgeHit(BaseModel):
    title: str
    content: str
    tags: Optional[str]= None
    score: float= Field(..., ge= 0)

class RetrieveKnowledgeOutput(BaseModel):
    ok: bool = True
    query: str
    hits: List[KnowledgeHit]


# TOOLS

# Tool 1

@tool
def account_lookup(email: str)-> Dict[str, Any]:
    """
    Look up a CultPass user by email in the external DB (cultpass.db).
    Returns structured account info (found/user_id/is_blocked).
    """
    email=(email or "").strip()
    if "@" not in email:
        return ToolError(error= "invalid_email", details={"email": email}).model_dump()
    
    db_path = _cultpass_db_path()
    if not db_path.exists():
        return ToolError(error="cultpass_db_not_found", details={"expected_path": str(db_path)}).model_dump()
    
    eng= _engine(str(db_path))
    row= _fetch_one(
        eng,
        """
        SELECT user_id, full_name, email, is_blocked
        FROM users
        WHERE lower(email) = lower(:email)
        LIMIT 1
        """,
        {"email": email},
    )

    if not row:
        return AccountLookupOutput(found=False).model_dump()
    
    return AccountLookupOutput(
        found= True,
        user_id= row.get("user_id"),
        full_name= row.get("full_name"),
        email=row.get("email"),
        is_blocked= bool(row.get("is_blocked"))
    ).model_dump()

# Tool 2

@tool
def subscription_status(user_id: Optional[str]= None, email: Optional[str]= None )-> Dict[str, Any]:
    """
    Check if a user has an active subscription (cultpass.db).
    Accepts user_id; if missing, tries to resolve via email.
    """
    db_path= _cultpass_db_path()
    if not db_path.exists():
        return ToolError(error= "cultpass_db_not_found", details={"expected_path": str(db_path)}).model_dump()
    eng= _engine(str(db_path))

    resolved_user_id= (user_id or "").strip() or None
    if not resolved_user_id:
        if not email:
            return ToolError(error="missing_user_id_or_email").model_dump()
        acc= account_lookup(email= email)
        if not acc.get("ok", False) or not acc.get("found"):
            return SubscriptionStatusOutput(found= False).model_dump()
        resolved_user_id= acc.get("user_id")
    
    row = _fetch_one(
        eng,
        """
        SELECT user_id, plan, status, renewal_date
        FROM subscriptions
        WHERE user_id = :user_id
        ORDER BY renewal_date DESC
        LIMIT 1
        """,
        {"user_id": resolved_user_id},
    )

    if not row:
        return SubscriptionStatusOutput(found=False, user_id=resolved_user_id).model_dump()

    status = (row.get("status") or "").lower()
    active = status in {"active", "trial", "paid"}  # ajustable a vuestro schema real

    return SubscriptionStatusOutput(
        found=True,
        user_id=row.get("user_id"),
        active_subscription=active,
        plan=row.get("plan"),
        status=row.get("status"),
        renewal_date=str(row.get("renewal_date")) if row.get("renewal_date") is not None else None,
    ).model_dump()

# Tool 3. Reservation lookup

def reservation_lookup(user_id: str, limit: int= 5)-> Dict[str, Any]:
    """
    List recent reservations for a user (cultpass.db).
    Useful for 'QR not showing' / 'cannot find booking' issues.
    """

    user_id= (user_id or "").strip()
    if not user_id:
        return ToolError(error= "missing_user_id").model_dump()

    db_path= _cultpass_db_path()
    if not db_path.exists():
        return ToolError(error="cultpass_db_not_found", details={"expected_path": str(db_path)}).model_dump()
    
    eng= _engine(str(db_path))
    rows= _fetch_all(
        eng,
        """
        SELECT reservation_id, experience_id, status, reserved_at
        FROM reservations
        WHERE user_id = :user_id
        ORDER BY reserved_at DESC
        LIMIT :limit
        """,
        {"user_id": user_id, "limit": int(limit)},

    )

    return ReservationLookupOutput(user_id= user_id, reservations= rows).model_dump()

# Tool 4. Retrieve knowledge 

def _simple_text_score()
        

