from core.tools import get_system_info, save_note, get_notes, add_todo, get_todos
from core.ollama_client import ollama_client
from web.app import app

def run_tests():
    print("[1] Testing System Telemetry...")
    info = get_system_info()
    assert "cpu_usage_percent" in info, "Missing CPU info"
    print(f"    CPU: {info['cpu_usage_percent']}% | RAM: {info['ram_percent']}% | Battery: {info['battery']['percent']}%")

    print("[2] Testing Local Productivity Database...")
    note = save_note("Quick Note", "This is a test note for my personal assistant.")
    assert note.get("success"), "Note saving failed"
    notes = get_notes()
    assert len(notes) > 0, "Note retrieval failed"
    print(f"    Saved note ID: {note['note_id']}, Total notes: {len(notes)}")

    todo = add_todo("Buy groceries", "high")
    assert todo.get("success"), "Todo saving failed"
    todos = get_todos()
    assert len(todos) > 0, "Todo retrieval failed"
    print(f"    Saved todo ID: {todo['todo_id']}, Total pending: {len(todos)}")

    print("[3] Testing Ollama connection probe...")
    online = ollama_client.is_online()
    print(f"    Ollama online status: {online}")

    print("[4] Testing Web App routes...")
    assert len(app.routes) > 5, "FastAPI routes missing"
    print(f"    FastAPI routes registered: {len(app.routes)}")

    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
