"""
provider.py - LLM Provider Interface

Supports:
- MockProvider: For testing without API calls
- OpenRouterProvider: Real LLM calls via OpenRouter API
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Generate a completion for the given messages.
        
        Returns:
            Dict with keys:
            - content: str (the response text)
            - tool_calls: Optional[List[Dict]] (if function calling)
            - finish_reason: str
        """
        pass


class MockProvider(LLMProvider):
    """Mock provider for testing - responds with predefined replies."""

    def __init__(self):
        self.call_count = 0
        self.conversation_history: List[Dict] = []

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Mock completion - simulates tool-use loop behavior.
        """
        self.call_count += 1
        self.conversation_history = messages.copy()

        # Get the last user message
        last_user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_msg = msg["content"]
                break

        # Check if last message was a tool result (stop looping)
        for msg in reversed(messages):
            if msg["role"] == "system" and "Tool" in msg["content"] and "' result:" in msg["content"]:
                # Previous turn was a tool result, give final response
                return {
                    "content": f"Tool execution completed. I ran the command you requested and got the results above. Is there anything else you'd like me to help with?",
                    "finish_reason": "stop"
                }

        # Simple mock responses based on user input
        user_lower = last_user_msg.lower()

        # Check if user wants to use a tool
        if "list files" in user_lower or "ls" in user_lower:
            return {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "bash",
                        "arguments": '{"command": "ls -la"}'
                    }
                }],
                "finish_reason": "tool_calls"
            }
        elif "read" in user_lower and "file" in user_lower:
            # Extract filename if possible
            words = last_user_msg.split()
            filename = "README.md"  # default
            for i, word in enumerate(words):
                if word.lower() in ["file", "read"] and i + 1 < len(words):
                    filename = words[i + 1].strip(".,!?")
                    break
            return {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "read_file",
                        "arguments": f'{{"filename": "{filename}"}}'
                    }
                }],
                "finish_reason": "tool_calls"
            }
        elif "write" in user_lower or "create" in user_lower:
            return {
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "write_file",
                        "arguments": '{"filename": "test.txt", "content": "Hello from mock provider!"}'
                    }
                }],
                "finish_reason": "tool_calls"
            }
        elif any(word in user_lower for word in ["exit", "quit", "bye", "stop"]):
            return {
                "content": "Goodbye! Thanks for testing the mini coding agent.",
                "finish_reason": "stop"
            }
        else:
            # Default conversational response
            return {
                "content": f"Mock response #{self.call_count}: I received your message: '{last_user_msg}'. How can I help you with coding today?",
                "finish_reason": "stop"
            }


class OpenRouterProvider(LLMProvider):
    """Real LLM provider using OpenRouter API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-3.5-turbo"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

        if not self.api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY environment variable or pass api_key.")

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Call OpenRouter API for completion."""
        import urllib.request
        import urllib.error

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mini-coding-agent",
            "X-Title": "Mini Coding Agent",
        }

        payload = {
            "model": self.model,
            "messages": messages,
        }

        # Add tools if provided
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))

            # Parse the response
            choice = result["choices"][0]
            message = choice["message"]

            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", None),
                "finish_reason": choice.get("finish_reason", "stop")
            }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise Exception(f"OpenRouter API error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"OpenRouter request failed: {str(e)}")


class MiniMaxProvider(LLMProvider):
    """
    MiniMax provider using OpenAI-compatible API.
    
    API Details:
    - Endpoint: https://api.minimax.chat/v1/text/chatcompletion_v2
    - Model: minimax/MiniMax-M2.7 (or other MiniMax models)
    - Auth: Bearer token in Authorization header
    """

    # MiniMax supported models (use as-is, no prefix needed)
    MODELS = {
        "MiniMax-M2.7": "MiniMax-M2.7",
        "MiniMax-M2.1": "MiniMax-M2.1",
        "MiniMax-M2.1-Lightning": "MiniMax-M2.1-Lightning",
        "MiniMax-M2.5": "MiniMax-M2.5",
        "MiniMax-M2.5-Lightning": "MiniMax-M2.5-Lightning",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "MiniMax-M2.7",
        base_url: str = "https://api.minimax.io/v1/text"
    ):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.model = model
        self.base_url = base_url

        if not self.api_key:
            raise ValueError(
                "MiniMax API key required. "
                "Set MINIMAX_API_KEY environment variable or pass api_key."
            )

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Call MiniMax API for completion.
        
        MiniMax uses OpenAI-compatible API at api.minimax.io.
        Model names are used directly (e.g., 'MiniMax-M2.7').
        """
        import urllib.request
        import urllib.error

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # MiniMax API uses model names directly without provider prefix
        model_id = self.model

        payload = {
            "model": model_id,
            "messages": messages,
        }

        # Add tools if provided - MiniMax uses standard OpenAI function format
        if tools:
            # MiniMax supports tools in OpenAI format
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{self.base_url}/chatcompletion_v2",
                data=data,
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))

            # Check if the response has an error in base_resp
            base_resp = result.get("base_resp", {})
            if base_resp.get("status_code") and base_resp["status_code"] != 0:
                error_msg = base_resp.get("status_msg", "unknown error")
                raise Exception(f"MiniMax API error: {error_msg} (code: {base_resp['status_code']})")

            # Check if choices is present and valid
            choices = result.get("choices")
            if not choices or len(choices) == 0:
                raise Exception(f"MiniMax returned no choices: {result}")

            # Parse the response - OpenAI compatible format
            choice = choices[0]
            message = choice.get("message", {})

            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", None),
                "finish_reason": choice.get("finish_reason", "stop")
            }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise Exception(f"MiniMax API error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"MiniMax request failed: {str(e)}")


class TestProvider(LLMProvider):
    """
    Test provider for testing - returns configurable mock responses.
    
    Unlike MockProvider which infers responses from user input,
    TestProvider allows you to pre-configure expected responses
    for deterministic testing.
    """

    def __init__(
        self,
        responses: Optional[List[Dict[str, Any]]] = None,
        raise_on_call: bool = False,
        call_error: str = "TestProvider error"
    ):
        """
        Initialize TestProvider.
        
        Args:
            responses: List of pre-configured responses to return in order.
                       Each dict should have keys: 'content' and/or 'tool_calls',
                       and optionally 'finish_reason'. If None, uses default response.
            raise_on_call: If True, raises exception on every call.
            call_error: Error message to raise when raise_on_call is True.
        """
        self.responses = responses or [{
            "content": "Test response",
            "finish_reason": "stop"
        }]
        self.call_count = 0
        self.conversation_history: List[Dict] = []
        self.raise_on_call = raise_on_call
        self.call_error = call_error
        self.calls: List[Dict[str, Any]] = []  # Track all calls for assertions

    def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Return a pre-configured mock response for testing.
        """
        self.call_count += 1
        self.conversation_history = messages.copy()
        
        # Track the call for test assertions
        self.calls.append({
            "call_number": self.call_count,
            "messages": messages.copy(),
            "tools": tools.copy() if tools else None
        })

        if self.raise_on_call:
            raise Exception(self.call_error)

        # Get response for this call (cycle through responses if needed)
        response_index = (self.call_count - 1) % len(self.responses)
        response = self.responses[response_index].copy()
        
        # Ensure required keys are present
        response.setdefault("finish_reason", "stop")
        response.setdefault("tool_calls", None)
        response.setdefault("content", "")
        
        return {
            "content": response["content"],
            "tool_calls": response.get("tool_calls"),
            "finish_reason": response["finish_reason"]
        }

    def reset(self):
        """Reset call count and conversation history."""
        self.call_count = 0
        self.conversation_history = []
        self.calls = []

    def add_response(self, response: Dict[str, Any]):
        """Add a response to the end of the response queue."""
        self.responses.append(response)


def create_provider(provider_type: str = "mock", **kwargs) -> LLMProvider:
    """Factory function to create a provider."""
    if provider_type.lower() == "mock":
        return MockProvider()
    elif provider_type.lower() in ["openrouter", "openai", "real"]:
        return OpenRouterProvider(**kwargs)
    elif provider_type.lower() == "minimax":
        return MiniMaxProvider(**kwargs)
    elif provider_type.lower() == "test":
        return TestProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
