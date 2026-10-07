import json
import logging
from typing import List, Dict, Any, Generator, Optional
from core.config import config
from core.llm_provider import llm_provider
from core.tools import TOOL_DEFINITIONS, execute_tool_call, get_system_info

logger = logging.getLogger("Agent")

class PersonalAgent:
    def __init__(self, model_name: Optional[str] = None):
        status = llm_provider.get_status_info()
        self.model_name = model_name or status["model"]
        self.conversation_history: List[Dict[str, Any]] = [
            {"role": "system", "content": config.SYSTEM_PROMPT}
        ]

    def reset_conversation(self):
        self.conversation_history = [
            {"role": "system", "content": config.SYSTEM_PROMPT}
        ]

    def set_model(self, model_name: str):
        self.model_name = model_name

    def run(self, user_prompt: str, max_steps: int = 5) -> Generator[Dict[str, Any], None, None]:
        """
        Execute agent reasoning loop.
        Yields events:
        - {"type": "thought", "content": "..."}
        - {"type": "tool_start", "tool": "...", "args": {...}}
        - {"type": "tool_result", "tool": "...", "result": ...}
        - {"type": "answer", "content": "..."}
        - {"type": "done", "full_answer": "..."}
        """
        # Append user message
        self.conversation_history.append({"role": "user", "content": user_prompt})

        # Check provider readiness
        if not llm_provider.is_configured():
            provider = llm_provider.get_active_provider()
            msg = (
                f"⚠️ **AI Provider ({provider}) is not yet configured or reachable.**\n\n"
                "**Quick Options:**\n"
                "1. **Free Cloud Option (Fast & 0 RAM usage)**:\n"
                "   Add your free Google Gemini API key to `.env` (`GEMINI_API_KEY=...`) or Groq key (`GROQ_API_KEY=...`).\n"
                "2. **Offline Local Option**:\n"
                "   Launch Ollama by running `ollama serve` in a terminal."
            )
            yield {"type": "answer", "content": msg}
            yield {"type": "done", "full_answer": msg}
            return

        current_step = 0
        while current_step < max_steps:
            current_step += 1
            yield {"type": "thought", "content": f"Thinking (Step {current_step})..."}

            # Call active LLM provider (Gemini / Groq / Ollama)
            response = llm_provider.chat(
                messages=self.conversation_history,
                tools=TOOL_DEFINITIONS,
                model=self.model_name
            )

            if "error" in response and "message" not in response:
                err_text = f"Agent encountered an error: {response.get('error')}"
                yield {"type": "answer", "content": err_text}
                yield {"type": "done", "full_answer": err_text}
                return

            assistant_msg = response.get("message", {})
            content = assistant_msg.get("content", "") or ""
            tool_calls = assistant_msg.get("tool_calls", [])

            # Check for native tool calls or fallback JSON parsing
            if not tool_calls and "```json" in content:
                try:
                    block = content.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(block)
                    if isinstance(parsed, dict) and "name" in parsed:
                        tool_calls = [{"function": {"name": parsed.get("name"), "arguments": parsed.get("arguments", {})}}]
                except Exception:
                    pass

            # If no tool calls, this is the final answer!
            if not tool_calls:
                self.conversation_history.append({"role": "assistant", "content": content})
                yield {"type": "answer", "content": content}
                yield {"type": "done", "full_answer": content}
                return

            # Append the assistant's decision to history
            self.conversation_history.append(assistant_msg)

            # Execute tool calls
            for call in tool_calls:
                func = call.get("function", {})
                name = func.get("name")
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}

                yield {"type": "tool_start", "tool": name, "args": args}
                result = execute_tool_call(name, args)
                yield {"type": "tool_result", "tool": name, "result": result}

                # Provide result back to the model
                tool_result_content = json.dumps(result, ensure_ascii=False)
                self.conversation_history.append({
                    "role": "tool",
                    "content": tool_result_content,
                    "name": name,
                    "tool_call_id": call.get("id", f"call_{name}")
                })

        # Max steps reached fallback
        final_msg = "Completed task operations."
        yield {"type": "answer", "content": final_msg}
        yield {"type": "done", "full_answer": final_msg}

agent = PersonalAgent()
