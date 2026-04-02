"""
agent.py - Agent Loop Core

Implements the classic tool-use loop:
1. Send messages to LLM
2. If LLM requests tool, execute it and return result
3. Repeat until LLM responds with final answer
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from messages import MessageHistory
from provider import LLMProvider
from tools import ToolRegistry


@dataclass
class AgentConfig:
    """Configuration for the agent."""
    max_iterations: int = 20
    max_tool_calls_per_iteration: int = 5
    verbose: bool = True


class Agent:
    """
    Main agent class implementing the tool-use loop.

    The agent:
    1. Maintains conversation history
    2. Sends messages to the LLM provider
    3. Executes tools when requested
    4. Continues until completion
    """

    def __init__(
        self,
        provider: LLMProvider,
        tools: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[AgentConfig] = None
    ):
        self.provider = provider
        self.tools = tools or ToolRegistry()
        self.config = config or AgentConfig()
        self.messages = MessageHistory()

        # Add system prompt if provided
        if system_prompt:
            self.messages.add_system(system_prompt)

    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the system prompt."""
        # Clear existing and add new
        self.messages.clear()
        self.messages.add_system(prompt)

    def run(self, user_input: str) -> str:
        """
        Run the agent with a user input.

        This implements the classic tool-use loop:
        1. Add user input to history
        2. Get LLM response
        3. If tool call, execute and add result, repeat
        4. Return final response
        """
        if self.config.verbose:
            print(f"\n{'='*50}")
            print(f"User: {user_input}")
            print(f"{'='*50}\n")

        # Add user message to history
        self.messages.add_user(user_input)

        # Main loop
        iteration = 0
        while iteration < self.config.max_iterations:
            iteration += 1

            if self.config.verbose:
                print(f"[Iteration {iteration}] Calling LLM...")

            # Get tools for this call
            toolspec = self.tools.get_tools_for_llm()

            # Get completion from provider
            response = self.provider.complete(
                messages=self.messages.get_messages_for_llm(),
                tools=toolspec if toolspec else None
            )

            content = response.get("content", "")
            tool_calls = response.get("tool_calls", None)
            finish_reason = response.get("finish_reason", "stop")

            # Add assistant response to history
            self.messages.add_assistant(content or "", tool_call=tool_calls)

            if self.config.verbose:
                if content:
                    print(f"LLM: {content[:200]}{'...' if len(content) > 200 else ''}")
                if tool_calls:
                    print(f"LLM wants to call {len(tool_calls)} tool(s)")

            # If no tool calls or stop, we're done
            if not tool_calls or finish_reason == "stop":
                if self.config.verbose:
                    print(f"\n[Agent finished with reason: {finish_reason}]")
                return content or "No response"

            # Execute tool calls
            for tool_call in tool_calls[:self.config.max_tool_calls_per_iteration]:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                tool_call_id = tool_call.get("id", f"call_unknown")
                raw_args = func.get("arguments", {})

                # Parse arguments (may be string or dict)
                if isinstance(raw_args, str):
                    try:
                        arguments = json.loads(raw_args)
                    except json.JSONDecodeError:
                        arguments = {"raw": raw_args}
                else:
                    arguments = raw_args

                if self.config.verbose:
                    print(f"  → Executing {tool_name}({arguments})")

                # Execute the tool
                result = self.tools.execute(tool_name, **arguments)

                # Add result to history with tool_call_id
                self.messages.add_tool_result(tool_call_id, tool_name, result)

                if self.config.verbose:
                    result_preview = result[:300].replace("\n", " ")
                    print(f"  ← Result: {result_preview}{'...' if len(result) > 300 else ''}")

        # Max iterations reached
        return "Error: Max iterations reached. The agent may be in an infinite loop."

    def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        print("\n" + "="*50)
        print("Mini Coding Agent - Interactive Mode")
        print("="*50)
        print("Type your task and press Enter.")
        print("Type 'exit', 'quit', or 'bye' to end.\n")

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "bye", "stop"]:
                    print("\nGoodbye!")
                    break

                # Run the agent
                response = self.run(user_input)

                print(f"\n{'='*50}")
                print(f"Agent: {response}")
                print(f"{'='*50}\n")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except EOFError:
                print("\n\nInput closed. Goodbye!")
                break

    def reset(self) -> None:
        """Reset the agent's message history."""
        system_messages = [m for m in self.messages.messages if m.role == "system"]
        self.messages.clear()
        for msg in system_messages:
            if msg.role == "system":
                self.messages.add_system(msg.content)

    def get_conversation_history(self) -> str:
        """Get the full conversation history as text."""
        return self.messages.get_conversation_text()


def create_coding_agent(provider: LLMProvider, **kwargs) -> Agent:
    """Factory function to create a coding agent with default system prompt."""

    default_system_prompt = """You are a helpful coding assistant with access to the following tools:

1. **bash** - Execute shell commands (ls, git, python, etc.)
   - Automatically translates Unix commands to Windows on Windows
   - Examples: ls -la, cat file.txt, grep pattern file

2. **read_file** - Read file contents
   - Examples: read_file(filename="README.md"), read_file(filename="main.py", max_lines=50)

3. **write_file** - Create or overwrite files
   - Examples: write_file(filename="test.txt", content="Hello"), write_file(filename="output.txt", content="...", append=true)

4. **edit_file** - Edit files with smart matching
   - Supports exact match (default), regex (regex=true), or fuzzy matching (fuzzy=true)
   - Examples: edit_file(filename="main.py", old_string="old", new_string="new")
   - Use regex=true for patterns: edit_file(filename="main.py", old_string="func\\\\(\\\\d+\\\\)", new_string="func(42)", regex=true)

5. **web_search** - Search the web using SearXNG
   - Requires SearXNG running at http://localhost:8080
   - Examples: web_search(query="Python tutorial"), web_search(query="AI news", count=5)

6. **web_fetch** - Fetch and read web pages
   - Examples: web_fetch(url="https://example.com"), web_fetch(url="https://api.github.com", max_chars=5000)

7. **python** - Execute Python code directly
   - Examples: python(code="print(2+2)"), python(code="import json; print(json.dumps({'a':1}))")

Use these tools to help the user with their coding tasks.
When you need to use a tool, make a tool call.
When you're done or the user says goodbye, respond with a friendly closing message.

Be concise and helpful in your responses."""

    return Agent(
        provider=provider,
        system_prompt=default_system_prompt,
        **kwargs
    )
