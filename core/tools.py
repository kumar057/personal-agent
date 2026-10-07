import os
import sys
import json
import sqlite3
import subprocess
import platform
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import psutil
from core.config import config

# Initialize Database
def get_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- TOOL IMPLEMENTATIONS ---

def get_system_info() -> Dict[str, Any]:
    """Get real-time laptop hardware and OS performance metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/")
        
        battery = psutil.sensors_battery()
        battery_info = {
            "percent": battery.percent if battery else "N/A",
            "power_plugged": battery.power_plugged if battery else True
        }
        
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "os": f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "cpu_usage_percent": cpu_percent,
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_total_gb": round(memory.total / (1024**3), 2),
            "ram_used_gb": round(memory.used / (1024**3), 2),
            "ram_percent": memory.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": disk.percent,
            "battery": battery_info,
            "system_boot_time": boot_time
        }
    except Exception as e:
        return {"error": f"Failed to retrieve system status: {str(e)}"}

def list_files(directory_path: str = ".") -> Dict[str, Any]:
    """List files and folders in a specified path."""
    try:
        target = Path(directory_path).resolve()
        if not target.exists():
            return {"error": f"Path '{directory_path}' does not exist."}
        
        items = []
        for item in target.iterdir():
            items.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": item.stat().st_size if item.is_file() else None,
                "modified": datetime.datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return {"directory": str(target), "count": len(items), "items": items[:100]}
    except Exception as e:
        return {"error": str(e)}

def read_file(file_path: str) -> Dict[str, Any]:
    """Read contents of a text file."""
    try:
        target = Path(file_path).resolve()
        if not target.exists() or not target.is_file():
            return {"error": f"File '{file_path}' not found."}
        
        # Limit preview to 30KB for safety
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(30000)
        return {"file_path": str(target), "content": content}
    except Exception as e:
        return {"error": str(e)}

def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Create or overwrite a file with given content."""
    try:
        target = Path(file_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "file_path": str(target), "bytes_written": len(content)}
    except Exception as e:
        return {"error": str(e)}

def run_command(command: str) -> Dict[str, Any]:
    """
    Run safe terminal command on the laptop (PowerShell / CMD).
    Dangerous commands are blocked.
    """
    dangerous_keywords = ["rmdir /s /q c:", "del /f /s /q c:", "format ", "diskpart", ":(){ :|:& };:"]
    cmd_lower = command.lower()
    for kw in dangerous_keywords:
        if kw in cmd_lower:
            return {"error": f"Command rejected: dangerous operation detected ({kw})."}
            
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=20
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:2000],
            "stderr": proc.stderr[:2000]
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out after 20 seconds."}
    except Exception as e:
        return {"error": str(e)}

# --- NOTES & PRODUCTIVITY ---

def save_note(title: str, content: str, tags: str = "") -> Dict[str, Any]:
    """Save a personal note or idea to local memory."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
            (title, content, tags)
        )
        note_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "note_id": note_id, "title": title}
    except Exception as e:
        return {"error": str(e)}

def get_notes(search_query: str = "") -> List[Dict[str, Any]]:
    """Retrieve personal notes, optionally filtered by search keywords."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        if search_query:
            param = f"%{search_query}%"
            cursor.execute("SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? ORDER BY id DESC", (param, param, param))
        else:
            cursor.execute("SELECT * FROM notes ORDER BY id DESC")
        rows = cursor.fetchall()
        notes = [dict(row) for row in rows]
        conn.close()
        return notes
    except Exception as e:
        return [{"error": str(e)}]

def add_todo(task: str, priority: str = "medium") -> Dict[str, Any]:
    """Add a new to-do task to personal planner."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (task, priority) VALUES (?, ?)",
            (task, priority.lower())
        )
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "todo_id": todo_id, "task": task, "priority": priority}
    except Exception as e:
        return {"error": str(e)}

def get_todos(status: str = "pending") -> List[Dict[str, Any]]:
    """Get to-dos filtered by status ('pending', 'completed', 'all')."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        if status == "all":
            cursor.execute("SELECT * FROM todos ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM todos WHERE status = ? ORDER BY id DESC", (status,))
        rows = cursor.fetchall()
        todos = [dict(row) for row in rows]
        conn.close()
        return todos
    except Exception as e:
        return [{"error": str(e)}]

def complete_todo(todo_id: int) -> Dict[str, Any]:
    """Mark a to-do item as completed."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE todos SET status = 'completed', completed_at = ? WHERE id = ?", (now, todo_id))
        conn.commit()
        conn.close()
        return {"success": True, "todo_id": todo_id}
    except Exception as e:
        return {"error": str(e)}

# --- WEB SEARCH ---

def web_search(query: str, max_results: int = 4) -> Dict[str, Any]:
    """Perform a live DuckDuckGo web search for up-to-date information."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return {"query": query, "results": results}
    except Exception as e:
        return {"error": f"Web search failed: {str(e)}"}

# --- KNOWLEDGE / RAG ---

def add_knowledge_document(filename: str, content: str) -> Dict[str, Any]:
    """Add a document (text, markdown, note) to the agent's knowledge base."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge_docs (filename, content) VALUES (?, ?) ON CONFLICT(filename) DO UPDATE SET content=excluded.content, indexed_at=CURRENT_TIMESTAMP",
            (filename, content)
        )
        conn.commit()
        conn.close()
        
        # Also store to disk
        file_path = Path(config.KNOWLEDGE_PATH) / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return {"success": True, "filename": filename, "characters": len(content)}
    except Exception as e:
        return {"error": str(e)}

def search_knowledge_base(query: str) -> Dict[str, Any]:
    """Search personal knowledge base documents for relevant answers."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT filename, content FROM knowledge_docs")
        docs = cursor.fetchall()
        conn.close()
        
        if not docs:
            return {"message": "Knowledge base is currently empty. Upload documents or add notes to begin."}
            
        words = [w.lower() for w in query.split() if len(w) > 2]
        matches = []
        for doc in docs:
            fname = doc["filename"]
            content = doc["content"]
            score = sum(content.lower().count(w) for w in words)
            if score > 0:
                # Extract excerpt
                matches.append({
                    "filename": fname,
                    "score": score,
                    "excerpt": content[:600]
                })
        matches.sort(key=lambda x: x["score"], reverse=True)
        return {"query": query, "matches": matches[:3]}
    except Exception as e:
        return {"error": str(e)}

# --- TOOL REGISTRY FOR AGENT ---

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Inspect real-time laptop diagnostics: CPU usage, RAM used/available, Battery percentage, Disk space, and OS info.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a PowerShell/CMD shell command on the laptop to check settings, list processes, or open utilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given folder path on the laptop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Path to list, defaults to current folder."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file."}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or write content to a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file to create or overwrite."},
                    "content": {"type": "string", "description": "Text content to save."}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note, reminder, or snippet to personal memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the note."},
                    "content": {"type": "string", "description": "Note content or text."},
                    "tags": {"type": "string", "description": "Optional comma-separated tags."}
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_notes",
            "description": "Search or retrieve personal notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {"type": "string", "description": "Keywords to search notes for. Leave empty to list all."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "Add a task or to-do to the user's planner.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Description of the task."},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority."}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_todos",
            "description": "Retrieve tasks from the to-do list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "completed", "all"], "description": "Filter by status."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a task complete by its ID number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "integer", "description": "ID of the task to mark completed."}
                },
                "required": ["todo_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date answers, news, documentation, or facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the local personal knowledge base and uploaded documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic or question to look up in the documents."}
                },
                "required": ["query"]
            }
        }
    }
]

# Dispatcher mapping
TOOL_MAP = {
    "get_system_info": get_system_info,
    "run_command": run_command,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "save_note": save_note,
    "get_notes": get_notes,
    "add_todo": add_todo,
    "get_todos": get_todos,
    "complete_todo": complete_todo,
    "web_search": web_search,
    "search_knowledge_base": search_knowledge_base,
}

def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
    func = TOOL_MAP.get(tool_name)
    if not func:
        return {"error": f"Tool '{tool_name}' not found."}
    try:
        return func(**arguments)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
