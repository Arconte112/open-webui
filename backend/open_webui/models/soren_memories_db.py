"""
Modelo para acceder a la base de datos externa de memorias (memories.db)
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

log = logging.getLogger(__name__)


class SorenMemory:
    """Representa una memoria de la BD externa"""
    def __init__(self, id: int, content: str, importance: int, 
                 created_at: str, updated_at: str, tags: str = None, metadata: str = None):
        self.id = id
        self.content = content
        self.importance = importance
        self.created_at = created_at
        self.updated_at = updated_at
        self.tags = self._parse_json(tags, [])
        self.metadata = self._parse_json(metadata, {})
    
    def _parse_json(self, value: str, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except:
            return default


class SorenMemoriesDB:
    """Acceso a la base de datos externa de memorias"""
    
    def __init__(self, db_path: str = None):
        # Usar la ruta de la BD de memorias externa
        if db_path is None:
            # Ruta por defecto en Windows WSL
            db_path = "/mnt/c/Users/raini/Documents/Programas/soren_def/open-webui/memories.db"
        
        self.db_path = db_path
        
    def _get_connection(self):
        """Obtiene una conexión a la BD"""
        return sqlite3.connect(self.db_path)
    
    def get_all_memories(self) -> List[SorenMemory]:
        """Obtiene todas las memorias de la BD"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, importance, created_at, updated_at, tags, metadata 
                FROM memories 
                ORDER BY importance DESC, updated_at DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            memories = []
            for row in rows:
                memory = SorenMemory(
                    id=row[0],
                    content=row[1],
                    importance=row[2],
                    created_at=row[3],
                    updated_at=row[4],
                    tags=row[5],
                    metadata=row[6]
                )
                memories.append(memory)
            
            log.info(f"Retrieved {len(memories)} memories from external DB")
            return memories
            
        except Exception as e:
            log.error(f"Error reading from memories.db: {e}")
            return []
    
    def get_memories_by_importance(self, min_importance: int = 5) -> List[SorenMemory]:
        """Obtiene memorias con importancia mayor o igual al valor dado"""
        all_memories = self.get_all_memories()
        return [m for m in all_memories if m.importance >= min_importance]


# Instancia global
soren_memories_db = SorenMemoriesDB()