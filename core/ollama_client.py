import json
import logging
from typing import List, Dict, Any, Optional, Generator
import httpx
from core.config import config

logger = logging.getLogger("OllamaClient")

class OllamaClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = httpx.Timeout(120.0, connect=10.0)

    def is_online(self) -> bool:
        """Check if local Ollama server is running."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/version")
                return res.status_code == 200
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """Get Ollama version."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/version")
                if res.status_code == 200:
                    return res.json().get("version", "unknown")
        except Exception:
            pass
        return None

    def list_models(self) -> List[Dict[str, Any]]:
        """List all models available locally in Ollama."""
        if not self.is_online():
            return []
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    return res.json().get("models", [])
        except Exception:
            pass
        return []

    def get_model_names(self) -> List[str]:
        models = self.list_models()
        return [m.get("name", "") for m in models if m.get("name")]

    def pull_model(self, model_name: str) -> Generator[Dict[str, Any], None, None]:
        """Stream model download status from Ollama."""
        url = f"{self.base_url}/api/pull"
        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, json={"name": model_name}) as response:
                for line in response.iter_lines():
                    if line:
                        try:
                            yield json.loads(line)
                        except Exception:
                            pass

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Ollama.
        Supports native tool calling if supported by the model, or fallback prompt.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json()
                else:
                    return {
                        "error": f"Ollama error {res.status_code}: {res.text}",
                        "message": {"role": "assistant", "content": f"Ollama Error: {res.text}"}
                    }
        except httpx.ConnectError:
            return {
                "error": "Cannot connect to Ollama. Is the Ollama server running? Run 'ollama serve' in terminal.",
                "message": {
                    "role": "assistant",
                    "content": "⚠️ Local Ollama service is not currently reachable. Please make sure Ollama is installed and running."
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": {"role": "assistant", "content": f"Unexpected error: {str(e)}"}
            }

ollama_client = OllamaClient()
