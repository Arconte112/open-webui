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
            db_path = "/mnt/c/Users/raini/Documents/Programas/soren_def/sorendb.db"
        
        self.db_path = db_path
        self._ensure_schema()
        
    def _get_connection(self):
        """Obtiene una conexión a la BD"""
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self):
        """Crea la tabla de memorias si no existe"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    importance INTEGER DEFAULT 5,
                    tags TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Trigger to maintain updated_at
            cur.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_memories_updated_at
                AFTER UPDATE ON memories
                BEGIN
                    UPDATE memories SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END;
                """
            )
            conn.commit()
            conn.close()
        except Exception as e:
            log.error(f"Error ensuring external memories schema: {e}")

    def create_memory(self, content: str, importance: int = 5, tags: Optional[list] = None, metadata: Optional[dict] = None) -> Optional[int]:
        """Crea una memoria en la BD externa y devuelve su ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            tags_json = json.dumps(tags) if tags else None
            metadata_json = json.dumps(metadata) if metadata else "{}"
            cursor.execute(
                """
                INSERT INTO memories (content, importance, tags, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (content, importance, tags_json, metadata_json),
            )
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
        except Exception as e:
            log.error(f"Error creating memory in external DB: {e}")
            return None

    def update_memory(self, id: int, content: Optional[str] = None, importance: Optional[int] = None,
                      tags: Optional[list] = None, metadata: Optional[dict] = None) -> bool:
        """Actualiza campos de una memoria por ID."""
        try:
            sets = []
            params = []
            if content is not None:
                sets.append("content = ?")
                params.append(content)
            if importance is not None:
                sets.append("importance = ?")
                params.append(importance)
            if tags is not None:
                sets.append("tags = ?")
                params.append(json.dumps(tags))
            if metadata is not None:
                sets.append("metadata = ?")
                params.append(json.dumps(metadata))
            if not sets:
                return False
            sets.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE memories SET {', '.join(sets)} WHERE id = ?"
            params.append(id)
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            ok = cursor.rowcount > 0
            conn.close()
            return ok
        except Exception as e:
            log.error(f"Error updating memory in external DB: {e}")
            return False

    def delete_memory(self, id: int) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (id,))
            conn.commit()
            ok = cursor.rowcount > 0
            conn.close()
            return ok
        except Exception as e:
            log.error(f"Error deleting memory in external DB: {e}")
            return False

    def clear_memories(self) -> int:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            conn.commit()
            count = cursor.rowcount
            conn.close()
            return count if count is not None else 0
        except Exception as e:
            log.error(f"Error clearing external memories: {e}")
            return 0

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
