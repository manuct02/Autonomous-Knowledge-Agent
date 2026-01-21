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
                                    root.parent / "data" / "core" / "cultpass_articles.jsonl,"
                                    ])

@lru_cache(maxsize= 4)
def _engine(sqlite_path: str)-> Engine:
    return create_engine(f"sqlite:///{sqlite_path}", echo= False, future= True)

def _fetch_one(engine: Engine, sql: str, params: Dict[str, Ant])-> Optional[Dict^[str, Any]]:
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

