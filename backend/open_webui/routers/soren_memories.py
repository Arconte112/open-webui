"""
API Router para gestionar las memorias de Soren
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from open_webui.utils.auth import get_verified_user
from open_webui.utils.soren_memories import get_formatted_memories, format_memories_for_prompt
from open_webui.utils.soren_memories_helper import add_memory_with_metadata, update_memory_metadata
from open_webui.models.memories import Memories

router = APIRouter()


class SorenMemoryCreate(BaseModel):
    text: str
    category: str = "general"
    importance: str = "medium"


class SorenMemoryUpdate(BaseModel):
    text: Optional[str] = None
    category: Optional[str] = None
    importance: Optional[str] = None


@router.get("/soren/memories")
async def get_soren_memories(user=Depends(get_verified_user)):
    """
    Obtiene todas las memorias formateadas del usuario actual
    """
    formatted = get_formatted_memories(user.id)
    return {
        "memories": formatted,
        "formatted_text": format_memories_for_prompt(user.id)
    }


@router.post("/soren/memories")
async def create_soren_memory(
    memory: SorenMemoryCreate,
    user=Depends(get_verified_user)
):
    """
    Crea una nueva memoria con categoría e importancia
    """
    success = add_memory_with_metadata(
        user_id=user.id,
        text=memory.text,
        category=memory.category,
        importance=memory.importance
    )
    
    if success:
        return {"message": "Memoria creada exitosamente"}
    else:
        raise HTTPException(status_code=500, detail="Error al crear la memoria")


@router.put("/soren/memories/{memory_id}")
async def update_soren_memory(
    memory_id: str,
    memory: SorenMemoryUpdate,
    user=Depends(get_verified_user)
):
    """
    Actualiza una memoria existente
    """
    success = update_memory_metadata(
        memory_id=memory_id,
        user_id=user.id,
        text=memory.text,
        category=memory.category,
        importance=memory.importance
    )
    
    if success:
        return {"message": "Memoria actualizada exitosamente"}
    else:
        raise HTTPException(status_code=404, detail="Memoria no encontrada")


@router.get("/soren/memories/test")
async def test_soren_memories(user=Depends(get_verified_user)):
    """
    Endpoint de prueba para verificar que las memorias funcionan
    """
    # Agregar algunas memorias de prueba
    test_memories = [
        ("Mi nombre es Soren", "personal", "high"),
        ("Prefiero programar en Python", "preferences", "medium"),
        ("Trabajo en el proyecto Open WebUI", "work", "high"),
        ("Me gusta usar FastAPI para APIs", "technical", "medium")
    ]
    
    for text, category, importance in test_memories:
        add_memory_with_metadata(user.id, text, category, importance)
    
    # Obtener las memorias formateadas
    formatted = format_memories_for_prompt(user.id)
    
    return {
        "message": "Memorias de prueba creadas",
        "formatted_output": formatted
    }