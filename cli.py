import sys
from core.agent import agent
from core.config import config
from core.ollama_client import ollama_client

def main():
    print("=" * 60)
    print(f"🤖 {config.PROJECT_NAME} - CLI Terminal Interface")
    print(f"Model: {agent.model_name}")
    print("Type 'exit' or 'quit' to close. Type 'status' for hardware health.")
    print("=" * 60)

    if not ollama_client.is_online():
        print("⚠️ Warning: Ollama is not running. Please start Ollama via 'ollama serve'.")

    while True:
        try:
            user_input = input("\nYou > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            if user_input.lower() == "status":
                from core.tools import get_system_info
                info = get_system_info()
                print(f"CPU: {info['cpu_usage_percent']}% | RAM: {info['ram_percent']}% | Battery: {info['battery']['percent']}%")
                continue

            print("\n[Aegis]")
            for event in agent.run(user_input):
                if event["type"] == "tool_start":
                    print(f"  ⚡ Running tool: {event['tool']}...")
                elif event["type"] == "done":
                    print(f"\n{event['full_answer']}")

        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

if __name__ == "__main__":
    main()
