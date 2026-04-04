# Mini Coding Agent

A minimalist coding agent implementation in Python with a classic tool-use loop.

## 🎯 Features

- **Cross-Platform Support** (Windows/Linux/Mac) — Automatic command translation
- **Multiple LLM Providers** (Mock, OpenRouter, MiniMax)
- **Rich Tool Set** (Bash, Read, Write, Edit, WebSearch, WebFetch, PythonREPL)
- **Automatic Context Compression** (Three-layer compression system)
- **CLI Interface** — Supports command and interactive modes

## 🏗️ Architecture

```
user input
    ↓
agent.py (Agent Loop)
    ↓
provider.py (LLM Interface)
    ├── MockProvider
    ├── OpenRouterProvider
    └── MiniMaxProvider
    ↓
tools.py (Tool Use)
    ├── BashTool
    ├── ReadTool
    ├── WriteTool
    ├── EditTool
    ├── WebSearchTool
    ├── WebFetchTool
    └── PythonREPLTool
    ↓
LLM (MiniMax M2.7 / OpenRouter Models)
```

## 📁 Directory Structure

```
mini_coding_agent/
├── agent.py              # Agent loop core
├── provider.py           # LLM interface (Mock/OpenRouter/MiniMax)
├── tools.py              # Tool implementations (Bash/Read/Write/Edit/Web etc.)
├── main.py               # CLI entry point
├── messages.py           # Message history management
├── platform_utils.py     # Cross-platform command translation
├── compactor.py          # Three-layer compression system
├── history_manager.py    # Conversation history management
├── .env                  # API Keys
├── .gitignore            # Git ignore settings
├── LICENSE               # MIT License
├── DEVELOPMENT_LOG_COMPRESSION.md  # Compression system details
└── README.md             # This file
```

## 📦 Requirements

- **Python 3.7+**
- **API Key** (MiniMax or OpenRouter)

### Environment Setup

```bash
# Clone project
git clone https://github.com/Sumo0221/mini-coding-agent.git
cd mini-coding-agent

# Install dependencies (if needed)
pip install python-dotenv requests

# Set API Key
# Method 1: Copy .env template and fill in your API Key
cp .env.example .env  # or edit .env directly

# Method 2: Use environment variables
export MINIMAX_API_KEY=your_key_here
# or
export OPENROUTER_API_KEY=your_key_here
```

## 🚀 Quick Start

### Basic Usage

```bash
# Use MiniMax (default)
python main.py --provider minimax --task "say hello"

# Use OpenRouter
python main.py --provider openrouter --task "write a hello world in python"

# Use Mock (for testing, no API Key needed)
python main.py --provider mock --task "echo hello"
```

### Interactive Mode

```bash
# Enter interactive mode
python main.py --provider minimax --interactive
```

### Test Mode

```bash
# Test specific tools
python main.py --provider mock --test-tools

# Run unit tests
python test_compactor.py
```

## 💻 Usage

### CLI Mode

```bash
python main.py --provider minimax --task "Create a hello.py for me"
```

### Interactive Mode

```bash
python main.py --provider minimax --interactive
# Then enter your question and press Enter, /exit to quit
```

### Tool List

| Tool | Function | Example |
|------|---------|---------|
| **BashTool** | Execute system commands | `"ls -la"`, `"Get-ChildItem"` (auto-translated on Windows)|
| **ReadTool** | Read file content | `"Read: path/to/file.py"` |
| **WriteTool** | Write to file | `"Write: path/to/file.py"` + content |
| **EditTool** | Edit file (replace text) | `"Edit: file.py"` + oldText + newText |
| **WebSearchTool** | Web search | `"Search: Python tutorial"` |
| **WebFetchTool** | Fetch web content | `"Fetch: https://example.com"` |
| **PythonREPLTool** | Python REPL | `"python: print('hello')"` |

### Tool Usage Example

```python
# Describe your need in the task, agent will automatically call tools
task = "Create hello.py that outputs 'Hello, World!' then run it"
```

## 🗜️ Three-Layer Compression System

When conversation history gets too long, the system automatically performs three-layer compression:

1. **Compression (Estimate)** — `estimate_tokens()`: Simple token count estimation
2. **Pruning (Judge)** — `should_compact()`: Determine if compression is needed
3. **Summarization (Summarize)** — `summarize_messages()`: Generate structured summary

### Basic Usage

```python
from compactor import Compactor, compact_messages

compactor = Compactor(preserve_recent=4, max_tokens=10000)
messages = [{"role": "user", "content": "..."}, ...]

if compactor.should_compact(messages):
    result = compactor.compact(messages)
```

For details, see: [DEVELOPMENT_LOG_COMPRESSION.md](DEVELOPMENT_LOG_COMPRESSION.md)

## 🔧 Configuration

### .env Template

```env
# MiniMax API (recommended)
MINIMAX_API_KEY=your_minimax_key_here

# OpenRouter (alternative)
OPENROUTER_API_KEY=your_openrouter_key_here
```

### Command Line Arguments

| Argument | Description | Default |
|---------|-------------|---------|
| `--provider` | LLM Provider (minimax/openrouter/mock) | minimax |
| `--task` | Task description | - |
| `--interactive` | Start interactive mode | False |
| `--test-tools` | Test tool functionality | False |
| `--max-iterations` | Max iterations | 20 |

## 📝 Output Example

```
=== Mini Coding Agent ===
Provider: minimax
Task: say hello

[Agent] Thinking...
[Agent] Responding: Hello! I'm a mini coding agent.
[Tool] BashTool: executed 'echo hello'
[Agent] Responding: Done!

=== Complete (1 iterations, 3 tool calls) ===
```

## 📄 License

MIT License - See [LICENSE](LICENSE)

## 🔗 Related Links

- [Development Log: Compression System](DEVELOPMENT_LOG_COMPRESSION.md)
- [GitHub Repo](https://github.com/Sumo0221/mini-coding-agent)
