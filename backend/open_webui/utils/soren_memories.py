"""
Soren Memories Utility
Recupera y formatea todas las memorias de la base de datos
agrupándolas por categoría con su id, contenido e importancia.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from open_webui.models.memories import Memories
from open_webui.models.soren_memories_db import soren_memories_db

log = logging.getLogger(__name__)


def parse_memory_content(content: str) -> Dict[str, Any]:
    """
    Intenta parsear el contenido de una memoria como JSON.
    Si falla, devuelve el contenido como texto plano.
    """
    try:
        # Intentar parsear como JSON
        data = json.loads(content)
        return {
            "category": data.get("category", "general"),
            "text": data.get("text", content),
            "importance": data.get("importance", "medium")
        }
    except (json.JSONDecodeError, TypeError):
        # Si no es JSON, asumir formato simple
        # Intentar detectar categoría por prefijos comunes
        content_lower = content.lower()
        category = "general"
        
        if any(word in content_lower for word in ["personal", "sobre mí", "about me"]):
            category = "personal"
        elif any(word in content_lower for word in ["trabajo", "work", "proyecto", "project"]):
            category = "work"
        elif any(word in content_lower for word in ["técnico", "technical", "código", "code"]):
            category = "technical"
        elif any(word in content_lower for word in ["preferencia", "preference", "gusto", "like"]):
            category = "preferences"
        
        return {
            "category": category,
            "text": content,
            "importance": "medium"
        }


def get_formatted_memories(user_id: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Recupera todas las memorias y las formatea agrupadas por categoría.
    
    Args:
        user_id: Si se especifica, solo recupera memorias de ese usuario
    
    Returns:
        Dict con memorias agrupadas por categoría
    """
    # Obtener memorias de la BD externa memories.db
    try:
        memories = soren_memories_db.get_all_memories()
        log.info(f"Retrieved {len(memories)} memories from external database")
    except Exception as e:
        log.error(f"Error retrieving memories from external DB: {e}")
        memories = []
    
    if not memories:
        log.warning("No memories found in external database")
        return {}
    
    # Agrupar por categoría basándose en tags o análisis del contenido
    grouped_memories = {}
    
    for memory in memories:
        # Determinar categoría basándose en tags o contenido
        category = "general"
        
        # Si tiene tags, usar el primer tag como categoría
        if memory.tags and len(memory.tags) > 0:
            category = memory.tags[0]
        else:
            # Analizar contenido para determinar categoría
            content_lower = memory.content.lower()
            if any(word in content_lower for word in ["personal", "alejandro", "horario"]):
                category = "personal"
            elif any(word in content_lower for word in ["proyecto", "trabajo", "desarrollo", "cliente"]):
                category = "work"
            elif any(word in content_lower for word in ["medicación", "salud", "medicina"]):
                category = "health"
            elif any(word in content_lower for word in ["preferencia", "prefiere", "gusta"]):
                category = "preferences"
        
        if category not in grouped_memories:
            grouped_memories[category] = []
        
        grouped_memories[category].append({
            "id": memory.id,
            "content": memory.content,
            "importance": memory.importance,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at
        })
    
    # Ordenar memorias por importancia (mayor primero) y fecha
    for category in grouped_memories:
        grouped_memories[category].sort(
            key=lambda x: (
                -x["importance"],  # Mayor importancia primero (negativo para invertir orden)
                x["updated_at"] if isinstance(x["updated_at"], (int, float)) else 0  # Más recientes primero
            )
        )
    
    return grouped_memories


def format_memories_for_prompt(user_id: Optional[str] = None) -> str:
    """
    Formatea las memorias para incluir en un system prompt.
    
    Returns:
        String formateado con todas las memorias
    """
    memories = get_formatted_memories(user_id)
    
    if not memories:
        return "No hay memorias disponibles."
    
    formatted_text = "=== MEMORIAS DEL SISTEMA ===\n\n"
    
    for category, items in memories.items():
        formatted_text += f"## {category.upper()}\n"
        
        for memory in items:
            formatted_text += f"- [{memory['id']}] (Importancia: {memory['importance']}) {memory['content']}\n"
        
        formatted_text += "\n"
    
    formatted_text += "=== FIN DE MEMORIAS ===\n"
    
    return formatted_text


# Variable global que contiene todas las memorias formateadas
def get_soren_memories() -> str:
    """
    Función principal que devuelve la variable soren_memories
    con todas las memorias formateadas.
    """
    return format_memories_for_prompt()


def get_soren_memories_cached(cache_duration: int = 300, user_id: Optional[str] = None) -> str:
    """
    Obtiene las memorias formateadas sin caché.
    
    Args:
        cache_duration: (ignorado, mantenido por compatibilidad)
        user_id: ID del usuario (opcional)
    """
    return format_memories_for_prompt(user_id)