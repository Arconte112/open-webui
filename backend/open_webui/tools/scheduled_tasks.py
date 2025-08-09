"""
title: Scheduled Tasks Manager
description: Create and manage scheduled tasks for automated prompts
author: open-webui
version: 1.0.0
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz

class Tools:
    def __init__(self):
        self.db_path = "/mnt/c/Users/raini/Documents/Programas/soren_def/sorendb.db"
        self.user_id = "2f1dbb34-dc80-45a1-8bd6-68c7791aefbd"
        self.timezone = pytz.timezone('America/Santo_Domingo')
        # Ensure DB schema has expected columns
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(scheduled_tasks)")
            cols = [c[1] for c in cur.fetchall()]
            if 'notification_summary' not in cols:
                cur.execute("ALTER TABLE scheduled_tasks ADD COLUMN notification_summary TEXT")
                conn.commit()
            conn.close()
        except Exception:
            # If anything fails here, create_task() will still attempt insert with available columns
            pass
    
    def get_db_connection(self) -> sqlite3.Connection:
        """Get a connection to the scheduler database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_task(
        self,
        task_name: str,
        notification_summary: str,
        prompt: str,
        frequency: str,
        time: Optional[str] = None,
        date: Optional[str] = None,
        weekday: Optional[str] = None,
        __user__: dict = {}
    ) -> str:
        """
        Create a new scheduled task.
        
        :param task_name: Descriptive name for the task
        :param notification_summary: Short, user-facing text for system notifications (keep it concise)
        :param prompt: The prompt to send when task executes
        :param frequency: 'once', 'hourly', 'daily', or 'weekly'
        :param time: Time in HH:MM format for recurring tasks (e.g., "14:30")
        :param date: Date in YYYY-MM-DD format for one-time tasks
        :param weekday: Day of week for weekly tasks (e.g., "monday", "tuesday")
        :return: Success or error message
        """
        try:
            # Validate notification summary
            if not notification_summary or not notification_summary.strip():
                return "❌ 'notification_summary' is required and cannot be empty"
            notification_summary = notification_summary.strip()
            # Keep summaries short for toast notifications
            if len(notification_summary) > 140:
                notification_summary = notification_summary[:140].rstrip() + "…"

            # Validate frequency
            valid_frequencies = ['once', 'hourly', 'daily', 'weekly']
            if frequency not in valid_frequencies:
                return f"❌ Invalid frequency. Must be one of: {', '.join(valid_frequencies)}"
            
            # Calculate next execution time
            current_time = datetime.now(self.timezone)
            next_execution = None
            scheduled_time = None
            scheduled_datetime = None
            weekday_num = None
            
            if frequency == 'once':
                if not date:
                    return "❌ For one-time tasks, you must provide a date (YYYY-MM-DD format)"
                try:
                    # Parse date and time
                    if time:
                        scheduled_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                    else:
                        scheduled_datetime = datetime.strptime(f"{date} 09:00", "%Y-%m-%d %H:%M")
                    
                    scheduled_datetime = self.timezone.localize(scheduled_datetime)
                    next_execution = scheduled_datetime
                    
                    if next_execution <= current_time:
                        return "❌ Scheduled time must be in the future"
                except ValueError:
                    return "❌ Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time"
            
            elif frequency == 'hourly':
                # Next execution is 1 hour from now
                next_execution = current_time + timedelta(hours=1)
            
            elif frequency == 'daily':
                if not time:
                    return "❌ For daily tasks, you must provide a time (HH:MM format)"
                try:
                    hour, minute = map(int, time.split(':'))
                    scheduled_time = time
                    next_execution = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_execution <= current_time:
                        next_execution += timedelta(days=1)
                except ValueError:
                    return "❌ Invalid time format. Use HH:MM (e.g., 14:30)"
            
            elif frequency == 'weekly':
                if not time or not weekday:
                    return "❌ For weekly tasks, you must provide both time (HH:MM) and weekday"
                
                # Convert weekday name to number
                weekdays = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                    'friday': 4, 'saturday': 5, 'sunday': 6
                }
                weekday_lower = weekday.lower()
                if weekday_lower not in weekdays:
                    return f"❌ Invalid weekday. Must be one of: {', '.join(weekdays.keys())}"
                
                weekday_num = weekdays[weekday_lower]
                
                try:
                    hour, minute = map(int, time.split(':'))
                    scheduled_time = time
                    
                    # Calculate next occurrence
                    days_ahead = weekday_num - current_time.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    
                    next_execution = current_time + timedelta(days=days_ahead)
                    next_execution = next_execution.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except ValueError:
                    return "❌ Invalid time format. Use HH:MM (e.g., 14:30)"
            
            # Insert into database
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Build insert dynamically to tolerate DBs created before new column existed
            cursor.execute("PRAGMA table_info(scheduled_tasks)")
            cols = [c[1] for c in cursor.fetchall()]

            if 'notification_summary' in cols:
                cursor.execute("""
                    INSERT INTO scheduled_tasks (
                        user_id, task_name, notification_summary, prompt, frequency,
                        scheduled_time, scheduled_datetime, weekday,
                        next_execution_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id, task_name, notification_summary, prompt, frequency,
                    scheduled_time, scheduled_datetime, weekday_num,
                    next_execution, current_time, current_time
                ))
            else:
                # Fallback insert without the new column
                cursor.execute("""
                    INSERT INTO scheduled_tasks (
                        user_id, task_name, prompt, frequency,
                        scheduled_time, scheduled_datetime, weekday,
                        next_execution_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id, task_name, prompt, frequency,
                    scheduled_time, scheduled_datetime, weekday_num,
                    next_execution, current_time, current_time
                ))
            
            conn.commit()
            task_id = cursor.lastrowid
            conn.close()
            
            # Format success message
            if frequency == 'once':
                exec_str = next_execution.strftime("%Y-%m-%d at %H:%M")
            elif frequency == 'hourly':
                exec_str = "every hour"
            elif frequency == 'daily':
                exec_str = f"daily at {time}"
            elif frequency == 'weekly':
                exec_str = f"every {weekday} at {time}"
            else:
                exec_str = "at scheduled time"
            
            return (
                "✅ Task '" + task_name + "' created successfully!\n"
                + "🔔 Summary: " + notification_summary + "\n"
                + "📅 Will execute: " + exec_str + "\n"
                + "🆔 Task ID: " + str(task_id)
            )
            
        except Exception as e:
            return f"❌ Error creating task: {str(e)}"
    
    def list_tasks(
        self,
        active_only: bool = True,
        limit: int = 10,
        __user__: dict = {}
    ) -> str:
        """
        List scheduled tasks.
        
        :param active_only: Show only active tasks (default: True)
        :param limit: Maximum number of tasks to show (default: 10)
        :return: Formatted list of tasks
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            if active_only:
                query = "SELECT * FROM scheduled_tasks WHERE is_active = 1 ORDER BY next_execution_at LIMIT ?"
            else:
                query = "SELECT * FROM scheduled_tasks ORDER BY next_execution_at DESC LIMIT ?"
            
            cursor.execute(query, (limit,))
            tasks = cursor.fetchall()
            
            if not tasks:
                return "📋 No scheduled tasks found."
            
            result = "📋 **Scheduled Tasks:**\n\n"
            
            for task in tasks:
                # Status emoji
                status = "✅" if task['is_active'] else "❌"
                
                # Frequency description
                freq_desc = task['frequency']
                if task['frequency'] == 'daily' and task['scheduled_time']:
                    freq_desc = f"Daily at {task['scheduled_time']}"
                elif task['frequency'] == 'weekly' and task['scheduled_time'] and task['weekday'] is not None:
                    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    freq_desc = f"Every {weekdays[task['weekday']]} at {task['scheduled_time']}"
                
                # Next execution
                next_exec = "N/A"
                if task['next_execution_at']:
                    next_dt = datetime.fromisoformat(task['next_execution_at'])
                    next_exec = next_dt.strftime("%Y-%m-%d %H:%M")
                
                # Execution count
                exec_count = task['execution_count'] or 0
                
                result += f"{status} **{task['task_name']}** (ID: {task['id']})\n"
                result += f"   📅 {freq_desc}\n"
                result += f"   ⏰ Next: {next_exec}\n"
                result += f"   🔄 Executed: {exec_count} times\n"
                # Notification summary (if present)
                notif = task['notification_summary'] if 'notification_summary' in task.keys() else None
                if notif:
                    result += f"   🔔 Summary: {notif}\n"
                result += f"   💬 Prompt: {task['prompt'][:50]}{'...' if len(task['prompt']) > 50 else ''}\n\n"
            
            conn.close()
            return result
            
        except Exception as e:
            return f"❌ Error listing tasks: {str(e)}"
    
    def delete_task(
        self,
        task_id: int,
        __user__: dict = {}
    ) -> str:
        """
        Delete a scheduled task.
        
        :param task_id: ID of the task to delete
        :return: Success or error message
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if task exists
            cursor.execute("SELECT task_name FROM scheduled_tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            
            if not task:
                conn.close()
                return f"❌ Task with ID {task_id} not found."
            
            # Delete the task
            cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            
            return f"✅ Task '{task['task_name']}' (ID: {task_id}) deleted successfully!"
            
        except Exception as e:
            return f"❌ Error deleting task: {str(e)}"
    
    def toggle_task(
        self,
        task_id: int,
        __user__: dict = {}
    ) -> str:
        """
        Toggle a task's active status (enable/disable).
        
        :param task_id: ID of the task to toggle
        :return: Success or error message
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get current status
            cursor.execute("SELECT task_name, is_active FROM scheduled_tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            
            if not task:
                conn.close()
                return f"❌ Task with ID {task_id} not found."
            
            # Toggle status
            new_status = 0 if task['is_active'] else 1
            cursor.execute("""
                UPDATE scheduled_tasks 
                SET is_active = ?, updated_at = ?
                WHERE id = ?
            """, (new_status, datetime.now(self.timezone), task_id))
            
            conn.commit()
            conn.close()
            
            status_text = "enabled" if new_status else "disabled"
            return f"✅ Task '{task['task_name']}' (ID: {task_id}) has been {status_text}!"
            
        except Exception as e:
            return f"❌ Error toggling task: {str(e)}"
    
    def task_info(
        self,
        task_id: int,
        __user__: dict = {}
    ) -> str:
        """
        Get detailed information about a specific task.
        
        :param task_id: ID of the task
        :return: Detailed task information
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
            task = cursor.fetchone()
            
            if not task:
                conn.close()
                return f"❌ Task with ID {task_id} not found."
            
            # Format detailed information
            result = f"📋 **Task Details:**\n\n"
            result += f"**Name:** {task['task_name']}\n"
            result += f"**ID:** {task['id']}\n"
            result += f"**Status:** {'✅ Active' if task['is_active'] else '❌ Inactive'}\n"
            result += f"**Frequency:** {task['frequency']}\n"
            
            if task['scheduled_time']:
                result += f"**Scheduled Time:** {task['scheduled_time']}\n"
            
            if task['weekday'] is not None:
                weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                result += f"**Weekday:** {weekdays[task['weekday']]}\n"
            
            if 'notification_summary' in task.keys() and task['notification_summary']:
                result += f"**Notification Summary:** {task['notification_summary']}\n\n"
            result += f"**Prompt:**\n{task['prompt']}\n\n"
            
            if task['next_execution_at']:
                next_dt = datetime.fromisoformat(task['next_execution_at'])
                result += f"**Next Execution:** {next_dt.strftime('%Y-%m-%d %H:%M')}\n"
            
            if task['last_executed_at']:
                last_dt = datetime.fromisoformat(task['last_executed_at'])
                result += f"**Last Executed:** {last_dt.strftime('%Y-%m-%d %H:%M')}\n"
            
            result += f"**Execution Count:** {task['execution_count'] or 0}\n"
            result += f"**Failed Attempts:** {task['fail_count'] or 0}\n"
            
            if task['last_error']:
                result += f"\n**Last Error:** {task['last_error']}\n"
            
            created_dt = datetime.fromisoformat(task['created_at'])
            result += f"\n**Created:** {created_dt.strftime('%Y-%m-%d %H:%M')}\n"
            
            conn.close()
            return result
            
        except Exception as e:
            return f"❌ Error getting task info: {str(e)}"
