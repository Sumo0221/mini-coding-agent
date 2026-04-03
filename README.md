# Mini Coding Agent

一個用 Python 實作的最簡單的 coding agent，具備經典的 tool-use loop。

## 🎯 特色功能

- **跨平台支援**（Windows/Linux/Mac）— 自動命令翻譯
- **多種 LLM Provider**（Mock、OpenRouter、MiniMax）
- **豐富工具集**（Bash、Read、Write、Edit、WebSearch、WebFetch、PythonREPL）
- **自動上下文壓縮**（三層壓縮系統）
- **CLI 界面** — 支援指令和互動模式

## 🏗️ 架構圖

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

## 📁 目錄結構

```
mini_coding_agent/
├── agent.py              # Agent 迴圈核心
├── provider.py           # LLM 介面（支援 Mock/OpenRouter/MiniMax）
├── tools.py              # 工具實作（Bash/Read/Write/Edit/Web等）
├── main.py               # CLI 入口
├── messages.py           # 訊息歷史管理
├── platform_utils.py     # 跨平台命令翻譯
├── compactor.py          # 三層壓縮系統
├── history_manager.py    # 對話歷史管理
├── .env                  # API Keys
├── .gitignore            # Git 忽略設定
├── LICENSE               # MIT License
├── DEVELOPMENT_LOG_COMPRESSION.md  # 壓縮系統詳細文件
└── README.md             # 本文件
```

## 📦 安裝需求

- **Python 3.7+**
- **API Key**（MiniMax 或 OpenRouter）

### 環境設定

```bash
# 複製專案
git clone https://github.com/Sumo0221/mini-coding-agent.git
cd mini-coding-agent

# 安裝依賴（如需要）
pip install python-dotenv requests

# 設定 API Key
# 方法一：複製 .env 範本並填入你的 API Key
cp .env.example .env  # 或直接編輯 .env

# 方法二：使用環境變數
export MINIMAX_API_KEY=your_key_here
# 或
export OPENROUTER_API_KEY=your_key_here
```

## 🚀 快速開始

### 基本用法

```bash
# 使用 MiniMax（預設）
python main.py --provider minimax --task "say hello"

# 使用 OpenRouter
python main.py --provider openrouter --task "write a hello world in python"

# 使用 Mock（測試用，不需要 API Key）
python main.py --provider mock --task "echo hello"
```

### 互動模式

```bash
# 進入互動式對話
python main.py --provider minimax --interactive
```

### 測試模式

```bash
# 測試特定工具
python main.py --provider mock --test-tools

# 執行單元測試
python test_compactor.py
```

## 💻 使用方式

### CLI 模式

```bash
python main.py --provider minimax --task "幫我寫一個 hello.py"
```

### 互動模式

```bash
python main.py --provider minimax --interactive
# 然後輸入你的問題，按 Enter 送出，輸入 /exit 結束
```

### 工具列表

| 工具 | 功能 | 範例 |
|------|------|------|
| **BashTool** | 執行系統命令 | `"ls -la"`, `"Get-ChildItem"`（Windows自動轉換）|
| **ReadTool** | 讀取檔案內容 | `"Read: path/to/file.py"` |
| **WriteTool** | 寫入檔案 | `"Write: path/to/file.py"` + 內容 |
| **EditTool** | 編輯檔案（替換文字）| `"Edit: file.py"` + oldText + newText |
| **WebSearchTool** | 網頁搜尋 | `"Search: Python tutorial"` |
| **WebFetchTool** | 擷取網頁內容 | `"Fetch: https://example.com"` |
| **PythonREPLTool** | Python 互動環境 | `"python: print('hello')"` |

### 工具使用範例

```python
# 在 task 中直接描述需求，agent 會自動調用工具
task = "幫我建立一個 hello.py，內容是輸出 'Hello, World!'，然後執行它"
```

## 🗜️ 三層壓縮系統

當對話歷史過長時，系統會自動進行三層壓縮：

1. **Compression (估算)** — `estimate_tokens()`: 簡單估算 token 數量
2. **Pruning (判斷)** — `should_compact()`: 判斷是否需要壓縮
3. **Summarization (摘要)** — `summarize_messages()`: 產生結構化摘要

### 基本用法

```python
from compactor import Compactor, compact_messages

compactor = Compactor(preserve_recent=4, max_tokens=10000)
messages = [{"role": "user", "content": "..."}, ...]

if compactor.should_compact(messages):
    result = compactor.compact(messages)
```

詳細說明請參考：[DEVELOPMENT_LOG_COMPRESSION.md](DEVELOPMENT_LOG_COMPRESSION.md)

## 🔧 設定

### .env 範本

```env
# MiniMax API（主要推薦）
MINIMAX_API_KEY=your_minimax_key_here

# OpenRouter（備選）
OPENROUTER_API_KEY=your_openrouter_key_here
```

### 命令列參數

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--provider` | LLM Provider（minimax/openrouter/mock） | minimax |
| `--task` | 執行的任務描述 | - |
| `--interactive` | 啟動互動模式 | False |
| `--test-tools` | 測試工具功能 | False |
| `--max-iterations` | 最大迭代次數 | 20 |

## 📝 輸出範例

```
=== Mini Coding Agent ===
Provider: minimax
Task: say hello

[Agent] Thinking...
[Agent] Responding: Hello! I'm a mini coding agent.
[Tool] BashTool: executed 'echo hello'
[Agent] Responding: Done!

=== 完成 (1 iterations, 3 tool calls) ===
```

## 📄 License

MIT License - 詳見 [LICENSE](LICENSE) 檔案

## 🔗 相關連結

- [開發日誌：壓縮系統](DEVELOPMENT_LOG_COMPRESSION.md)
- [GitHub Repo](https://github.com/Sumo0221/mini-coding-agent)
