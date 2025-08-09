"""
Endpoints para gestionar memorias desde la BD externa (sorendb.db)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

from open_webui.utils.auth import get_verified_user
from open_webui.models.soren_memories_db import soren_memories_db

router = APIRouter()


class ExternalMemoryCreate(BaseModel):
    content: str
    importance: int = 5
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None


class ExternalMemoryUpdate(BaseModel):
    content: Optional[str] = None
    importance: Optional[int] = None
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None


def _to_epoch(ts: Any) -> Optional[int]:
    if ts is None:
        return None
    # If ts is already numeric seconds
    try:
        if isinstance(ts, (int, float)):
            # assume seconds
            return int(ts)
        # Try ISO or sqlite datetime string
        return int(datetime.fromisoformat(str(ts)).timestamp())
    except Exception:
        return None


@router.get("/soren/external-memories")
async def list_external_memories(user=Depends(get_verified_user)):
    items = soren_memories_db.get_all_memories()
    data = [
        {
            "id": m.id,
            "content": m.content,
            "importance": m.importance,
            "tags": m.tags,
            "metadata": m.metadata,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
            "updated_at_epoch": _to_epoch(m.updated_at),
        }
        for m in items
    ]
    return {"memories": data}


@router.post("/soren/external-memories")
async def create_external_memory(body: ExternalMemoryCreate, user=Depends(get_verified_user)):
    new_id = soren_memories_db.create_memory(
        content=body.content,
        importance=body.importance,
        tags=body.tags,
        metadata=body.metadata,
    )
    if new_id is None:
        raise HTTPException(status_code=500, detail="Failed to create memory")
    return {"id": new_id}


@router.put("/soren/external-memories/{memory_id}")
async def update_external_memory(memory_id: int, body: ExternalMemoryUpdate, user=Depends(get_verified_user)):
    ok = soren_memories_db.update_memory(
        id=memory_id,
        content=body.content,
        importance=body.importance,
        tags=body.tags,
        metadata=body.metadata,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found or not updated")
    return {"ok": True}


@router.delete("/soren/external-memories/{memory_id}")
async def delete_external_memory(memory_id: int, user=Depends(get_verified_user)):
    ok = soren_memories_db.delete_memory(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"ok": True}


@router.delete("/soren/external-memories")
async def clear_external_memories(user=Depends(get_verified_user)):
    count = soren_memories_db.clear_memories()
    return {"deleted": count}

