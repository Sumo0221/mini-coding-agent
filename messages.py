"""
messages.py - Message History Management

Simple message history for the mini coding agent.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_call: Optional[Dict[str, Any]] = None
    tool_call_id: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class MessageHistory:
    """Manages the conversation history."""

    def __init__(self, max_messages: int = 100):
        self.messages: List[Message] = []
        self.max_messages = max_messages

    def add_user(self, content: str) -> None:
        """Add a user message."""
        self.messages.append(Message(role="user", content=content))

    def add_assistant(self, content: str, tool_call: Optional[Dict] = None) -> None:
        """Add an assistant message."""
        self.messages.append(Message(
            role="assistant",
            content=content,
            tool_call=tool_call
        ))

    def add_tool_result(self, tool_call_id: str, tool_name: str, result: str) -> None:
        """Add a tool result message with proper tool_call_id."""
        self.messages.append(Message(
            role="tool",
            content=f"Tool '{tool_name}' result: {result}",
            tool_call_id=tool_call_id
        ))

    def add_system(self, content: str) -> None:
        """Add a system message."""
        self.messages.append(Message(role="system", content=content))

    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """Get messages in OpenAI-compatible format."""
        result = []
        for msg in self.messages:
            if msg.role == "tool":
                # Tool results need tool_call_id for proper function calling
                result.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or f"call_{uuid.uuid4().hex[:12]}",
                    "content": msg.content
                })
            elif msg.role == "assistant" and msg.tool_call:
                # Include tool_calls in assistant message for function calling
                assistant_msg = {
                    "role": msg.role,
                    "content": msg.content if msg.content else ""
                }
                # Add tool calls if present
                if msg.tool_call:
                    # Handle both OpenAI and MiniMax tool_call formats
                    tool_calls = []
                    if isinstance(msg.tool_call, list):
                        for tc in msg.tool_call:
                            if isinstance(tc, dict):
                                func = tc.get("function", tc)
                                tool_calls.append({
                                    "id": tc.get("id", f"call_{uuid.uuid4().hex[:12]}"),
                                    "type": "function",
                                    "function": {
                                        "name": func.get("name", ""),
                                        "arguments": func.get("arguments", "{}") if isinstance(func.get("arguments"), str) else json.dumps(func.get("arguments", {}))
                                    }
                                })
                    assistant_msg["tool_calls"] = tool_calls
                result.append(assistant_msg)
            else:
                result.append({
                    "role": msg.role,
                    "content": msg.content
                })
        return result

    def get_conversation_text(self) -> str:
        """Get a simple text representation of the conversation."""
        lines = []
        for msg in self.messages:
            lines.append(f"[{msg.role.upper()}] {msg.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)

    def get_recent(self, n: int = 10) -> List[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:] if n > 0 else self.messages
