# Mini Coding Agent

一個用 Python 實作的最簡單的 coding agent，具備經典的 tool-use loop。

## 功能特色

- **跨平台支援**：自動將 Unix 命令翻譯成 Windows 等價命令
- **Provider 介面**：支援 MockProvider（測試用）和 OpenRouter、MiniMax（真實 LLM）
- **豐富工具集**：
  - BashTool（執行命令，自動翻譯 Unix → Windows）
  - ReadTool（讀檔）
  - WriteTool（寫檔）
  - EditTool（編輯檔案，支援 regex 和 fuzzy matching）
  - WebSearchTool（網路搜尋 via SearXNG）
  - WebFetchTool（抓取網頁內容）
  - PythonREPLTool（直接執行 Python 程式碼）
- **Agent 迴圈**：經典的 tool-use loop，支援 function calling
- **CLI 界面**：互動模式和單一任務模式

## 目錄結構

```
mini_coding_agent/
├── platform_utils.py  # 跨平台命令翻譯工具
├── provider.py        # LLM 介面（Mock + OpenRouter + MiniMax）
├── tools.py           # Tool 實作（所有工具）
├── agent.py          # Agent 迴圈核心
├── main.py           # CLI 入口
├── messages.py       # 訊息歷史管理
└── README.md         # 使用說明
```

## 安裝需求

- Python 3.7+
- 無需額外 dependencies（使用標準 library）

## 快速開始

### 1. 測試模式（不需要 API Key）

```bash
cd C:\Butler_Sumo\Temp\mini_coding_agent
python main.py --test
```

### 2. 互動模式 - Mock Provider

```bash
python main.py
```

### 3. 互動模式 - OpenRouter

```bash
# 設定 API Key
set OPENROUTER_API_KEY=your_api_key_here

# 啟動
python main.py --provider openrouter --model openai/gpt-3.5-turbo
```

### 4. 單一任務模式

```bash
python main.py --provider mock --task "list files"
python main.py --provider openrouter --task "create a hello world Python file"
```

## 跨平台命令翻譯

BashTool 會自動將 Unix 命令翻譯成 Windows 等價命令：

| Unix 命令 | Windows 等價 |
|----------|-------------|
| `ls -la` | `dir /b` |
| `cat file.txt` | `type file.txt` |
| `grep pattern file` | `findstr pattern file` |
| `pwd` | `cd` |
| `rm file.txt` | `del file.txt` |
| `cp src dst` | `copy src dst` |
| `mv src dst` | `move src dst` |
| `touch file.txt` | `type nul > file.txt` |
| `clear` | `cls` |

## 可用工具

| 工具名稱 | 功能 | 範例 |
|---------|------|------|
| `bash` | 執行 shell 命令 | `bash(command="ls -la")` |
| `read_file` | 讀取檔案 | `read_file(filename="test.py")` |
| `write_file` | 寫入檔案 | `write_file(filename="test.py", content="...")` |
| `edit_file` | 編輯檔案 | `edit_file(filename="test.py", old_string="...", new_string="...")` |
| `web_search` | 網路搜尋 | `web_search(query="Python tutorial")` |
| `web_fetch` | 抓取網頁 | `web_fetch(url="https://example.com")` |
| `python` | 執行 Python | `python(code="print(2+2)")` |

### EditTool 進階用法

EditTool 支援三種匹配模式：

1. **精確匹配**（預設）：
```python
edit_file(filename="test.py", old_string="hello", new_string="world")
```

2. **Regex 匹配**：
```python
edit_file(filename="test.py", old_string=r"func\(\d+\)", new_string="func(42)", regex=true)
```

3. **Fuzzy 匹配**：
```python
edit_file(filename="test.py", old_string="Helo", new_string="Hello", fuzzy=true)
```

### WebSearchTool 設定

WebSearchTool 需要 SearXNG 實例。預設 URL：`http://localhost:8080`

啟動本地 SearXNG：
```bash
# 使用 Docker
docker run -d -p 8080:8080 searxng/searxng

# 或在 C:\tools\searxng 查看既有安裝
```

### WebFetchTool 用法

```python
# 抓取網頁
web_fetch(url="https://httpbin.org/html", max_chars=5000)

# 自動處理編碼（UTF-8、cp950、big5 等）
```

### PythonREPLTool 用法

```python
# 簡單計算
python(code="2+2")  # 回傳: 4

# 複雜程式碼
python(code="import json; print(json.dumps({'a': 1}))")

# 多行程式碼
python(code="for i in range(3):\n    print(i)")
```

## 程式碼範例

### 基本使用

```python
from provider import create_provider
from agent import create_coding_agent

# 建立 Mock Provider
provider = create_provider("mock")

# 建立 Agent
agent = create_coding_agent(provider)

# 執行任務
response = agent.run("list files in current directory")
print(response)
```

### 使用 MiniMax

```python
from provider import create_provider
from agent import create_coding_agent

# MiniMax Provider
provider = create_provider(
    "minimax",
    api_key="your_api_key",
    model="MiniMax-M2.7"
)

agent = create_coding_agent(provider)
response = agent.run("create a simple Python hello world script")
```

### 手動新增工具

```python
from provider import create_provider
from agent import create_coding_agent
from tools import Tool, ToolRegistry

class MyTool(Tool):
    @property
    def name(self):
        return "my_tool"

    @property
    def description(self):
        return "Does something useful"

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
            "required": ["input"]
        }

    def execute(self, input):
        return f"Result: {input}"

# 建立 Agent 並註冊工具
provider = create_provider("mock")
registry = ToolRegistry()
registry.register(MyTool())
agent = create_coding_agent(provider, tools=registry)
```

## 環境變數

| 變數名稱 | 說明 |
|---------|------|
| `OPENROUTER_API_KEY` | OpenRouter API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `MINIMAX_API_KEY` | MiniMax API Key |

## Agent 迴圈運作原理

```
┌─────────────────┐
│  User Input     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Add to History │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Call LLM       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Response   │
│  (text + tools) │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌──────────────┐
│ Stop? │  │ Execute Tool │
└───┬───┘  └──────┬───────┘
    │             │
    ▼             │
┌───────┐         │
│ Done  │◄────────┘
└───────┘    (loop back)
```

## 發展記錄

### 2026-04-01 - 重大更新
- 新增 `platform_utils.py`：跨平台命令翻譯
- 新增 `WebSearchTool`：網路搜尋（需 SearXNG）
- 新增 `WebFetchTool`：網頁內容抓取
- 新增 `PythonREPLTool`：直接執行 Python 程式碼
- 新增 `EditTool` 進階功能：regex 和 fuzzy matching
- 改進 `BashTool`：自動翻譯 Unix → Windows 命令
- 改進編碼處理：支援 UTF-8、cp950、big5 等

### 2026-04-01 - 初始版本
- Provider 介面（Mock + OpenRouter）
- 基本工具（Bash/Read/Write）
- Agent 迴圈核心
- CLI 界面
- 訊息歷史管理

## License

MIT License
