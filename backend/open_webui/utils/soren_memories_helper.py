"""
Helper para gestionar memorias con categorías e importancia
"""

import json
from open_webui.models.memories import Memories


def add_memory_with_metadata(
    user_id: str, 
    text: str, 
    category: str = "general", 
    importance: str = "medium"
) -> bool:
    """
    Agrega una memoria con metadatos (categoría e importancia).
    
    Args:
        user_id: ID del usuario
        text: Contenido de la memoria
        category: Categoría (personal, work, technical, preferences, general)
        importance: Importancia (high, medium, low)
    
    Returns:
        bool: True si se agregó exitosamente
    """
    content_data = {
        "text": text,
        "category": category,
        "importance": importance
    }
    
    try:
        memory = Memories.insert_new_memory(
            user_id=user_id,
            content=json.dumps(content_data)
        )
        return memory is not None
    except Exception as e:
        print(f"Error al agregar memoria: {e}")
        return False


def update_memory_metadata(
    memory_id: str,
    user_id: str,
    text: str = None,
    category: str = None,
    importance: str = None
) -> bool:
    """
    Actualiza una memoria existente manteniendo los metadatos.
    """
    # Obtener memoria actual
    memory = Memories.get_memory_by_id(memory_id)
    if not memory:
        return False
    
    # Parsear contenido actual
    try:
        current_data = json.loads(memory.content)
    except:
        current_data = {"text": memory.content, "category": "general", "importance": "medium"}
    
    # Actualizar campos si se proporcionan
    if text is not None:
        current_data["text"] = text
    if category is not None:
        current_data["category"] = category
    if importance is not None:
        current_data["importance"] = importance
    
    # Guardar actualización
    return Memories.update_memory_by_id_and_user_id(
        id=memory_id,
        user_id=user_id,
        content=json.dumps(current_data)
    ) is not None


# Ejemplos de uso
if __name__ == "__main__":
    # Ejemplo de cómo agregar memorias
    user_id = "example_user_id"
    
    # Memorias personales
    add_memory_with_metadata(
        user_id, 
        "Mi nombre es Soren y trabajo como desarrollador de software",
        category="personal",
        importance="high"
    )
    
    # Preferencias
    add_memory_with_metadata(
        user_id,
        "Prefiero usar Python para el backend y React para el frontend",
        category="preferences",
        importance="medium"
    )
    
    # Información técnica
    add_memory_with_metadata(
        user_id,
        "Siempre usar async/await para operaciones I/O en Python",
        category="technical",
        importance="high"
    )
    
    # Información de trabajo
    add_memory_with_metadata(
        user_id,
        "Estoy trabajando en el proyecto Open WebUI",
        category="work",
        importance="medium"
    )