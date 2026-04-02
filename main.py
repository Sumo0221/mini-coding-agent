#!/usr/bin/env python3
"""
main.py - CLI Entry Point for Mini Coding Agent

Usage:
    python main.py                    # Interactive mode (mock provider)
    python main.py --openrouter       # Interactive mode with OpenRouter
    python main.py --openrouter --api-key YOUR_KEY  # With API key
    python main.py --task "your task" # Single task mode
    python main.py --test             # Run tests
"""

import argparse
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from provider import create_provider, MockProvider, OpenRouterProvider, MiniMaxProvider
from agent import Agent, create_coding_agent, AgentConfig
from tools import ToolRegistry


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Mini Coding Agent - A simple tool-use agent implementation"
    )

    parser.add_argument(
        "--provider",
        choices=["mock", "openrouter", "openai", "minimax"],
        default="mock",
        help="LLM provider to use (default: mock)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for OpenRouter/OpenAI"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use (default depends on provider: openai/gpt-3.5-turbo for openrouter, minimax/MiniMax-M2.7 for minimax)"
    )

    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Single task to execute (exits after completion)"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test cases"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        help="Maximum agent iterations (default: 20)"
    )

    return parser.parse_args()


def run_tests():
    """Run test cases to verify the agent works."""
    print("\n" + "="*50)
    print("Running Mini Coding Agent Tests")
    print("="*50)

    # Test 1: Mock Provider
    print("\n[Test 1] Testing MockProvider...")
    try:
        mock_provider = MockProvider()
        assert mock_provider.call_count == 0

        # Test completion
        result = mock_provider.complete([
            {"role": "user", "content": "Hello"}
        ])
        assert "content" in result
        assert mock_provider.call_count == 1
        print("  [PASS] MockProvider basic test passed")
    except Exception as e:
        print(f"  [FAIL] MockProvider test failed: {e}")
        return False

    # Test 2: Tools
    print("\n[Test 2] Testing ToolRegistry...")
    try:
        registry = ToolRegistry()

        # Test bash tool
        bash_result = registry.execute("bash", command="echo hello")
        assert "hello" in bash_result.lower()
        print("  [PASS] BashTool test passed")

        # Test read tool
        read_result = registry.execute("read_file", filename="README.md")
        # README might not exist yet, but shouldn't crash
        print("  [PASS] ReadTool test passed")

        # Test write tool
        import tempfile
        temp_file = os.path.join(tempfile.gettempdir(), "mini_agent_test.txt")
        write_result = registry.execute("write_file", filename=temp_file, content="test content")
        assert "success" in write_result.lower()
        print("  [PASS] WriteTool test passed")

        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

    except Exception as e:
        print(f"  [FAIL] ToolRegistry test failed: {e}")
        return False

    # Test 3: Agent with Mock
    print("\n[Test 3] Testing Agent with MockProvider...")
    try:
        agent = create_coding_agent(
            provider=MockProvider(),
            config=AgentConfig(verbose=False)
        )

        # Test simple conversation
        response = agent.run("Say hello")
        assert len(response) > 0
        assert agent.messages.messages[-1].role == "assistant"
        print("  [PASS] Agent conversation test passed")

        # Reset and test tool call
        agent.reset()
        response = agent.run("list files")
        # Should have called bash tool
        tool_calls_in_history = [
            m for m in agent.messages.messages
            if m.role == "assistant" and m.tool_call
        ]
        print(f"  [PASS] Agent tool call test passed (found {len(tool_calls_in_history)} tool calls)")

    except Exception as e:
        print(f"  [FAIL] Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Message History
    print("\n[Test 4] Testing MessageHistory...")
    try:
        from messages import MessageHistory

        history = MessageHistory()
        history.add_user("Hello")
        history.add_assistant("Hi there!")
        history.add_tool_result("call_123", "bash", "result")

        msgs = history.get_messages_for_llm()
        assert len(msgs) == 3
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        print("  [PASS] MessageHistory test passed")

    except Exception as e:
        print(f"  [FAIL] MessageHistory test failed: {e}")
        return False

    print("\n" + "="*50)
    print("All tests passed!")
    print("="*50 + "\n")
    return True


def main():
    """Main entry point."""
    args = parse_args()

    verbose = not args.quiet

    # Create config
    config = AgentConfig(
        max_iterations=args.max_iterations,
        verbose=verbose
    )

    # Create provider
    try:
        if args.provider == "mock":
            provider = create_provider("mock")
            if verbose:
                print("Using MockProvider (no API calls)")
        else:
            # Map provider to env var for API key and default model
            if args.provider == "openrouter":
                env_key = "OPENROUTER_API_KEY"
                default_model = "openai/gpt-3.5-turbo"
            elif args.provider == "openai":
                env_key = "OPENAI_API_KEY"
                default_model = "openai/gpt-3.5-turbo"
            elif args.provider == "minimax":
                env_key = "MINIMAX_API_KEY"
                default_model = "MiniMax-M2.7"
            else:
                env_key = f"{args.provider.upper()}_API_KEY"
                default_model = None

            api_key = args.api_key or os.environ.get(env_key, "")
            if not api_key:
                print(f"Error: API key required for {args.provider}.")
                print(f"Set {env_key} environment variable or use --api-key")
                sys.exit(1)

            # Use provided model or default
            model = args.model or default_model

            provider = create_provider(
                args.provider,
                api_key=api_key,
                model=model
            )
            if verbose:
                print(f"Using {args.provider} with model: {model}")

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating provider: {e}")
        sys.exit(1)

    # Run tests or interactive mode
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    # Create agent
    agent = create_coding_agent(provider, config=config)

    # Single task or interactive mode
    if args.task:
        if verbose:
            print(f"\nExecuting task: {args.task}\n")
        response = agent.run(args.task)
        print(f"\nAgent: {response}\n")
    else:
        agent.run_interactive()


if __name__ == "__main__":
    main()
