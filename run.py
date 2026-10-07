import uvicorn
import webbrowser
import threading
import time
from core.config import config
from core.llm_provider import llm_provider
from core.ollama_client import ollama_client

def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://{config.HOST}:{config.PORT}")

def main():
    info = llm_provider.get_status_info()
    
    print("=" * 60)
    print(f"🚀 Starting {config.PROJECT_NAME} v{config.VERSION}")
    print(f"🌐 Web UI: http://{config.HOST}:{config.PORT}")
    
    if info["configured"]:
        print(f"🟢 Active Engine: {info['provider_name']}")
        print(f"🧠 Model: {info['model']}")
    else:
        print("⚠️ No AI provider configured yet. Add API key in .env or via Web UI.")

    if ollama_client.is_online():
        print(f"🟢 Ollama Local Service: Online (v{ollama_client.get_version()})")
    else:
        print("ℹ️  Ollama Local Service: Offline (Using Cloud API)")
        
    print("=" * 60)
    print("💡 Running cleanly with quiet background logging.")
    print("   Press CTRL+C anytime in this window to stop the server.")
    print("=" * 60)

    # Automatically open web UI
    threading.Thread(target=open_browser, daemon=True).start()

    # Launch FastAPI Server with access_log=False to prevent polling spam
    uvicorn.run("web.app:app", host=config.HOST, port=config.PORT, reload=False, access_log=False)

if __name__ == "__main__":
    main()
