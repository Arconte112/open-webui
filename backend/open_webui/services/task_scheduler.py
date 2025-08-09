"""
OpenWebUI Task Scheduler Service
Handles execution of scheduled tasks by creating new chats and sending prompts
"""

import asyncio
import sqlite3
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pytz
import aiohttp
 

from open_webui.models.chats import Chats, ChatForm
from open_webui.models.messages import Messages
from open_webui.models.users import Users
from open_webui.models.models import Models
from open_webui.socket.main import get_event_emitter, sio

logger = logging.getLogger(__name__)


class OpenWebUIScheduler:
    """Task scheduler service for OpenWebUI"""
    
    def __init__(self):
        self.db_path = "/mnt/c/Users/raini/Documents/Programas/soren_def/sorendb.db"
        self.user_id = "2f1dbb34-dc80-45a1-8bd6-68c7791aefbd"
        self.running = False
        self.timezone = pytz.timezone('America/Santo_Domingo')  # Dominican Republic timezone
        logger.info("Task scheduler initialized")
    
    async def start(self):
        """Start the scheduler service"""
        self.running = True
        logger.info("Task scheduler started")
        check_count = 0
        
        while self.running:
            try:
                check_count += 1
                if check_count % 4 == 0:  # Log every 2 minutes
                    logger.info(f"Task scheduler is running (check #{check_count})")
                
                await self.check_and_execute_tasks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def stop(self):
        """Stop the scheduler service"""
        self.running = False
        logger.info("Task scheduler stopped")
    
    def get_db_connection(self) -> sqlite3.Connection:
        """Get a connection to the scheduler database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    async def check_and_execute_tasks(self):
        """Check for pending tasks and execute them"""
        try:
            current_time = datetime.now(self.timezone)
            logger.info(f"Checking for tasks at: {current_time}")
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get all active tasks that are due
            # Using strftime to normalize timezone for comparison
            cursor.execute("""
                SELECT * FROM scheduled_tasks 
                WHERE is_active = 1 
                AND next_execution_at <= ?
                ORDER BY next_execution_at
            """, (current_time.isoformat(),))
            
            tasks = cursor.fetchall()
            logger.info(f"Found {len(tasks)} tasks to execute")
            
            for task in tasks:
                try:
                    await self.execute_task(dict(task))
                except Exception as e:
                    logger.error(f"Error executing task {task['id']}: {e}")
                    await self.handle_task_error(task['id'], str(e))
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error checking tasks: {e}")
    
    async def execute_task(self, task: Dict[str, Any]):
        """Execute a single scheduled task"""
        logger.info(f"Executing task: {task['task_name']} (ID: {task['id']})")
        
        try:
            # Get the full model configuration including tools
            model = Models.get_model_by_id("soren")
            if not model:
                logger.error("Soren model not found")
                raise Exception("Soren model not found")
            
            # Extract model metadata including tools
            model_meta = model.meta if hasattr(model, 'meta') else {}
            model_params = model.params if hasattr(model, 'params') else {}
            
            # Get tool IDs from model metadata
            tool_ids = []
            if model_meta:
                # Check for toolIds (camelCase - used by frontend)
                if 'toolIds' in model_meta:
                    tool_ids = model_meta.get('toolIds', [])
                # Fallback to tool_ids (snake_case)
                elif 'tool_ids' in model_meta:
                    tool_ids = model_meta.get('tool_ids', [])
            
            # Log the model configuration for debugging
            logger.info(f"Model meta: {model_meta}")
            logger.info(f"Model params: {model_params}")
            logger.info(f"Tool IDs found: {tool_ids}")
            
            # Create new chat for this task execution
            chat_title = f"📅 {task['task_name']} - {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M')}"
            
            # Create chat data with full model configuration
            chat_data = {
                "title": chat_title,
                "history": {
                    "messages": {},
                    "currentId": None
                },
                "models": ["soren"],  # Using your custom Soren model
                "params": model_params,  # Include model parameters
                "meta": {
                    "tags": ["scheduled-task"],
                    "toolIds": tool_ids,  # Include tool IDs directly in chat meta
                    "model_meta": model_meta  # Include model metadata with tools
                }
            }
            
            # Insert new chat
            chat_form = ChatForm(chat=chat_data)
            chat = Chats.insert_new_chat(self.user_id, chat_form)
            
            if not chat:
                raise Exception("Failed to create chat")
            
            logger.info(f"Created new chat: {chat.id}")
            
            # Format the prompt with the task marker
            formatted_prompt = f"<TAREA PROGRAMADA>\n{task['prompt']}"
            
            # Create message in the chat
            message_id = str(uuid.uuid4())
            message_data = {
                "id": message_id,
                "parentId": None,
                "childrenIds": [],
                "role": "user",
                "content": formatted_prompt,
                "timestamp": int(datetime.now().timestamp()),
                "models": ["soren"],
                "model": "soren",
                "done": True,
                "context": None,
                "toolIds": tool_ids  # Include tool IDs in the message
            }
            
            # Add message to chat history with proper format
            chat_dict = chat.chat
            if "history" not in chat_dict:
                chat_dict["history"] = {"messages": {}, "currentId": None}
            
            chat_dict["history"]["messages"][message_id] = message_data
            chat_dict["history"]["currentId"] = message_id
            
            # Ensure models are set in chat
            if "models" not in chat_dict or not chat_dict["models"]:
                chat_dict["models"] = ["soren"]
            
            # Update chat with the message
            updated_chat = Chats.update_chat_by_id(chat.id, chat_dict)
            
            if updated_chat:
                logger.info(f"Task message sent to chat {chat.id}")
                
                # Emit WebSocket event to refresh chat list in UI
                await self.emit_new_chat_event(updated_chat)

                # Trigger AI response via standard chat pipeline so UI updates stream
                try:
                    await self.trigger_ai_response(chat.id, message_id)
                    logger.info(f"AI response triggered for chat {chat.id}")
                except Exception as e:
                    logger.error(f"Failed to trigger AI response: {e}")

                # System notifications disabled by request
            
            # Update task execution info
            await self.update_task_after_execution(task)
            
        except Exception as e:
            logger.error(f"Error in execute_task: {e}")
            raise

    
    
    async def update_task_after_execution(self, task: Dict[str, Any]):
        """Update task after successful execution"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Update execution count and last executed time
            current_time = datetime.now(self.timezone)
            
            # Calculate next execution time based on frequency
            next_execution = None
            
            if task['frequency'] == 'once':
                # One-time task, deactivate it
                cursor.execute("""
                    UPDATE scheduled_tasks 
                    SET is_active = 0, 
                        last_executed_at = ?,
                        execution_count = execution_count + 1,
                        fail_count = 0
                    WHERE id = ?
                """, (current_time, task['id']))
            else:
                # Calculate next execution
                next_execution = self.calculate_next_execution(
                    task['frequency'],
                    task.get('scheduled_time'),
                    task.get('weekday'),
                    current_time
                )
                
                cursor.execute("""
                    UPDATE scheduled_tasks 
                    SET last_executed_at = ?,
                        next_execution_at = ?,
                        execution_count = execution_count + 1,
                        fail_count = 0
                    WHERE id = ?
                """, (current_time, next_execution, task['id']))
            
            conn.commit()
            logger.info(f"Task {task['id']} updated successfully. Next execution: {next_execution}")
            
        finally:
            conn.close()
    
    async def handle_task_error(self, task_id: int, error_message: str):
        """Handle task execution error"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get current fail count
            cursor.execute("SELECT fail_count FROM scheduled_tasks WHERE id = ?", (task_id,))
            result = cursor.fetchone()
            fail_count = result['fail_count'] + 1 if result else 1
            
            # Update fail count and error message
            cursor.execute("""
                UPDATE scheduled_tasks 
                SET fail_count = ?,
                    last_error = ?,
                    is_active = CASE WHEN ? >= 3 THEN 0 ELSE is_active END
                WHERE id = ?
            """, (fail_count, error_message, fail_count, task_id))
            
            if fail_count >= 3:
                logger.error(f"Task {task_id} failed 3 times, deactivating")
            
            conn.commit()
            
        finally:
            conn.close()
    
    def calculate_next_execution(self, frequency: str, scheduled_time: Optional[str], 
                                weekday: Optional[int], base_time: datetime) -> datetime:
        """Calculate the next execution time based on frequency"""
        if frequency == 'hourly':
            return base_time + timedelta(hours=1)
        
        elif frequency == 'daily' and scheduled_time:
            # Parse time (HH:MM)
            hour, minute = map(int, scheduled_time.split(':'))
            next_time = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_time <= base_time:
                next_time += timedelta(days=1)
            
            return next_time
        
        elif frequency == 'weekly' and scheduled_time and weekday is not None:
            # Parse time
            hour, minute = map(int, scheduled_time.split(':'))
            
            # Calculate days until target weekday
            current_weekday = base_time.weekday()
            days_ahead = weekday - current_weekday
            
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            next_time = base_time + timedelta(days=days_ahead)
            next_time = next_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return next_time
        
        else:
            # Default to 1 hour from now
            return base_time + timedelta(hours=1)
    
    async def add_ai_response_to_chat(self, chat_id: str, ai_message: str):
        """Add the AI response to the chat"""
        try:
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                logger.error(f"Chat {chat_id} not found")
                return
            
            # Create AI message
            message_id = str(uuid.uuid4())
            message_data = {
                "id": message_id,
                "parentId": None,
                "childrenIds": [],
                "role": "assistant",
                "content": ai_message,
                "timestamp": int(datetime.now().timestamp()),
                "models": ["soren"],
                "model": "soren",
                "done": True,
                "context": None
            }
            
            # Add message to chat history
            chat_dict = chat.chat
            if "history" not in chat_dict:
                chat_dict["history"] = {"messages": {}, "currentId": None}
            
            chat_dict["history"]["messages"][message_id] = message_data
            chat_dict["history"]["currentId"] = message_id
            
            # Update chat
            Chats.update_chat_by_id(chat_id, chat_dict)
            logger.info(f"AI response saved to chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Error saving AI response to chat: {e}")
    
    async def trigger_ai_response(self, chat_id: str, message_id: str):
        """Trigger AI response by calling the OpenWebUI API using the standard pipeline.
        Uses chat_id and message_id so websocket events update the exact message.
        """
        try:
            # Get the chat to have the full context
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                logger.error(f"Chat {chat_id} not found")
                return
            
            # Get the full model configuration including tools
            model = Models.get_model_by_id("soren")
            model_params = {}
            tool_ids = []
            
            if model:
                if hasattr(model, 'params') and model.params:
                    model_params = model.params
                    logger.info(f"Model params: {model_params}")
                
                # Check if model has tool_ids in params or meta
                if hasattr(model, 'meta') and model.meta:
                    # Frontend uses camelCase: toolIds
                    if 'toolIds' in model.meta:
                        tool_ids = model.meta.get('toolIds', [])
                    # Fallback to snake_case if exists
                    elif 'tool_ids' in model.meta:
                        tool_ids = model.meta.get('tool_ids', [])
                
                # Also check params for tool_ids
                if not tool_ids and 'tool_ids' in model_params:
                    tool_ids = model_params.get('tool_ids', [])
                
                logger.info(f"Found tool_ids: {tool_ids}")
                logger.info(f"Full model object: {model.__dict__ if hasattr(model, '__dict__') else 'No __dict__'}")
            
            # Call the OpenWebUI OpenAI endpoint
            async with aiohttp.ClientSession() as session:
                url = "http://localhost:8080/api/chat/completions"
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjJmMWRiYjM0LWRjODAtNDVhMS04YmQ2LTY4Yzc3OTFhZWZiZCJ9.PT0uItYnGXJW8a4jYs9xvEwPjwgEj7Hztci71c3SfmA"
                }
                
                # Build messages array from chat history
                messages = []
                if chat.chat.get("history", {}).get("messages", {}):
                    for _msg_id, msg in chat.chat["history"]["messages"].items():
                        messages.append({
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        })

                # Build payload targeting the specific message in the chat via id/chat_id
                payload = {
                    "model": "soren",
                    "stream": False,
                    "tool_ids": tool_ids,
                    "chat_id": chat_id,
                    "id": message_id,
                    "messages": messages,
                }
                
                # Add model params including tools if available
                if model_params:
                    # If there are tools defined in the model params, include them
                    if "tools" in model_params:
                        payload["tools"] = model_params["tools"]
                    # Include other relevant params
                    for key in ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]:
                        if key in model_params:
                            payload[key] = model_params[key]
                
                logger.info(f"Sending request to trigger AI response for chat {chat_id}")
                logger.info(f"Request URL: {url}")
                logger.info(f"Payload: {json.dumps(payload, indent=2)}")
                
                async with session.post(url, json=payload, headers=headers) as response:
                    logger.info(f"Response status: {response.status}")
                    response_text = await response.text()

                    if response.status == 200:
                        # Try to persist assistant message so it's visible when opening later
                        try:
                            result = json.loads(response_text)
                            logger.info(f"AI response received for chat {chat_id}")
                            logger.info(f"Response preview: {str(result)[:200]}...")

                            if result.get("choices") and len(result["choices"]) > 0:
                                ai_message = result["choices"][0]["message"].get("content", "")
                                if ai_message:
                                    await self.add_ai_response_to_chat(chat_id, ai_message)
                                    logger.info(f"AI response added to chat {chat_id}")

                                    updated_chat = Chats.get_chat_by_id(chat_id)
                                    if updated_chat:
                                        await self.emit_chat_update_event(updated_chat)
                            else:
                                logger.error(f"No choices in response: {result}")
                        except Exception as e:
                            logger.error(f"Failed to parse or save response JSON: {e}")
                            logger.error(f"Response text: {response_text[:500]}")
                    else:
                        logger.error(f"API request failed with status {response.status}")
                        logger.error(f"Error response: {response_text[:500]}")
                
        except Exception as e:
            logger.error(f"Error triggering AI response: {e}")
            # Don't raise, just log - the message is still in the chat
    
    async def emit_new_chat_event(self, chat):
        """Emit WebSocket event to notify about new chat"""
        try:
            # Get user sessions from the socket pool
            from open_webui.socket.main import USER_POOL
            
            user_sessions = USER_POOL.get(self.user_id, [])
            if not user_sessions:
                logger.info(f"No active sessions for user {self.user_id}")
                return
            
            # Emit chat:new event to all user sessions
            for session_id in user_sessions:
                await sio.emit(
                    "chat:new",
                    {
                        "chat": {
                            "id": chat.id,
                            "title": chat.title,
                            "updated_at": chat.updated_at,
                            "created_at": chat.created_at,
                            "archived": chat.archived,
                            "pinned": chat.pinned,
                            "meta": chat.meta
                        }
                    },
                    to=session_id
                )
            
            logger.info(f"Emitted chat:new event for chat {chat.id} to {len(user_sessions)} sessions")
            
        except Exception as e:
            logger.error(f"Error emitting chat event: {e}")
            # Don't fail the task execution if WebSocket fails
    
    async def emit_chat_update_event(self, chat):
        """Emit WebSocket event to notify about chat update"""
        try:
            # Get user sessions from the socket pool
            from open_webui.socket.main import USER_POOL
            
            user_sessions = USER_POOL.get(self.user_id, [])
            if not user_sessions:
                logger.info(f"No active sessions for user {self.user_id}")
                return
            
            # Emit chat:update event to all user sessions
            for session_id in user_sessions:
                await sio.emit(
                    "chat:update",
                    {
                        "chat": {
                            "id": chat.id,
                            "title": chat.title,
                            "updated_at": chat.updated_at,
                            "created_at": chat.created_at,
                            "archived": chat.archived,
                            "pinned": chat.pinned,
                            "meta": chat.meta
                        }
                    },
                    to=session_id
                )
            
            logger.info(f"Emitted chat:update event for chat {chat.id} to {len(user_sessions)} sessions")
            
        except Exception as e:
            logger.error(f"Error emitting chat update event: {e}")


# Global instance
scheduler_instance = None
