import os
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from core.config import config
from core.ollama_client import ollama_client

logger = logging.getLogger("LLMProvider")

class LLMProvider:
    def __init__(self):
        self.timeout = httpx.Timeout(90.0, connect=10.0)

    def get_active_provider(self) -> str:
        provider = config.AI_PROVIDER
        # Auto-detect if not explicitly set
        if config.GEMINI_API_KEY:
            return "gemini"
        elif config.GROQ_API_KEY:
            return "groq"
        elif config.OPENROUTER_API_KEY:
            return "openrouter"
        elif ollama_client.is_online():
            return "ollama"
        return provider

    def is_configured(self) -> bool:
        provider = self.get_active_provider()
        if provider == "gemini":
            return bool(config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_free_gemini_key_here")
        elif provider == "groq":
            return bool(config.GROQ_API_KEY and config.GROQ_API_KEY != "your_free_groq_key_here")
        elif provider == "openrouter":
            return bool(config.OPENROUTER_API_KEY)
        elif provider == "ollama":
            return ollama_client.is_online()
        return False

    def get_status_info(self) -> Dict[str, Any]:
        provider = self.get_active_provider()
        configured = self.is_configured()
        
        provider_names = {
            "gemini": "Google Gemini (Free Cloud)",
            "groq": "Groq Cloud (Free Llama 3.3 70B)",
            "openrouter": "OpenRouter (Free Tier)",
            "ollama": "Ollama (Offline Local)"
        }
        
        default_model = "unknown"
        if provider == "gemini":
            default_model = config.GEMINI_DEFAULT_MODEL
        elif provider == "groq":
            default_model = config.GROQ_DEFAULT_MODEL
        elif provider == "ollama":
            default_model = config.OLLAMA_DEFAULT_MODEL

        return {
            "provider": provider,
            "provider_name": provider_names.get(provider, provider),
            "configured": configured,
            "model": default_model,
            "ollama_online": ollama_client.is_online()
        }

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        provider = self.get_active_provider()

        if provider == "gemini":
            return self._call_gemini(messages, tools, model or config.GEMINI_DEFAULT_MODEL)
        elif provider == "groq":
            return self._call_groq(messages, tools, model or config.GROQ_DEFAULT_MODEL)
        elif provider == "openrouter":
            return self._call_openrouter(messages, tools, model or "meta-llama/llama-3.3-70b-instruct:free")
        elif provider == "ollama":
            return ollama_client.chat(model or config.OLLAMA_DEFAULT_MODEL, messages, tools)
        else:
            return {
                "error": f"Unknown or unconfigured provider: {provider}",
                "message": {"role": "assistant", "content": "Please configure your API key in .env or start Ollama."}
            }

    def _call_gemini(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str) -> Dict[str, Any]:
        if not config.GEMINI_API_KEY:
            return {
                "error": "Gemini API key is missing. Add GEMINI_API_KEY in your .env file.",
                "message": {"role": "assistant", "content": "⚠️ Google Gemini API key is missing. Please add `GEMINI_API_KEY=your_key` in your `.env` file."}
            }
        
        # Ensure model is a valid Gemini model, not a local Ollama name like llama3.2
        if not model or not model.startswith("gemini"):
            model = config.GEMINI_DEFAULT_MODEL
            
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.GEMINI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    choice = data.get("choices", [{}])[0]
                    msg = choice.get("message", {})
                    return {"message": msg}
                else:
                    return {
                        "error": f"Gemini API error {res.status_code}: {res.text}",
                        "message": {"role": "assistant", "content": f"Gemini Error ({res.status_code}): {res.text}"}
                    }
        except Exception as e:
            return {
                "error": str(e),
                "message": {"role": "assistant", "content": f"Gemini Connection Error: {str(e)}"}
            }

    def _call_groq(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str) -> Dict[str, Any]:
        if not config.GROQ_API_KEY:
            return {
                "error": "Groq API key is missing. Add GROQ_API_KEY in your .env file.",
                "message": {"role": "assistant", "content": "⚠️ Groq API key is missing. Please add `GROQ_API_KEY=your_key` in your `.env` file."}
            }
        
        # Ensure model is a valid Groq model
        if not model or model.startswith("gemini"):
            model = config.GROQ_DEFAULT_MODEL

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.6
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    choice = data.get("choices", [{}])[0]
                    msg = choice.get("message", {})
                    return {"message": msg}
                else:
                    return {
                        "error": f"Groq API error {res.status_code}: {res.text}",
                        "message": {"role": "assistant", "content": f"Groq Error ({res.status_code}): {res.text}"}
                    }
        except Exception as e:
            return {
                "error": str(e),
                "message": {"role": "assistant", "content": f"Groq Connection Error: {str(e)}"}
            }

    def _call_openrouter(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str) -> Dict[str, Any]:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    choice = data.get("choices", [{}])[0]
                    return {"message": choice.get("message", {})}
                else:
                    return {
                        "error": f"OpenRouter API error {res.status_code}: {res.text}",
                        "message": {"role": "assistant", "content": f"OpenRouter Error: {res.text}"}
                    }
        except Exception as e:
            return {
                "error": str(e),
                "message": {"role": "assistant", "content": f"OpenRouter Connection Error: {str(e)}"}
            }

llm_provider = LLMProvider()
