# Compactor - 三層記憶壓縮系統

根據 claw-code 的三層記憶壓縮系統實作的 Python 版本。

## 三層壓縮機制

1. **Compression (估算)** - `estimate_tokens()`: 簡單估算 token 數量
2. **Pruning (判斷)** - `should_compact()`: 判斷是否需要壓縮
3. **Summarization (摘要)** - `summarize_messages()`: 產生結構化摘要

## 安裝

```bash
# 直接複製 compactor.py 到你的專案
```

## 使用方法

### 基本用法

```python
from compactor import Compactor, compact_messages

# 方法一：使用類別
compactor = Compactor(preserve_recent=4, max_tokens=10000)

messages = [
    {"role": "user", "content": "幫我寫一個 Python 程式"},
    {"role": "assistant", "content": "好的，這是一個簡單的 Python 程式..."},
    {"role": "tool", "content": "檔案已建立：demo.py"},
    {"role": "user", "content": "再幫我加一個功能"},
    {"role": "assistant", "content": "已加入新功能"},
    {"role": "user", "content": "測試一下"},
    {"role": "assistant", "content": "測試通過"},
]

# 檢查是否需要壓縮
if compactor.should_compact(messages):
    result = compactor.compact(messages)
else:
    result = messages

# 方法二：使用快速函式
result = compact_messages(messages, preserve_recent=4, max_tokens=10000)
```

### 參數說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `preserve_recent` | 4 | 保留最近 N 條原始消息 |
| `max_tokens` | 10000 | 觸發壓縮的 token 閾值 |

### API

#### `estimate_tokens(text: str) -> int`
估算文字的 token 數量（簡單估算：長度 / 4 + 1）

#### `should_compact(messages: list) -> bool`
判斷是否需要壓縮（消息數超過 preserve_recent 且總 token 超過 max_tokens）

#### `summarize_messages(messages: list) -> str`
產生結構化摘要，輸出格式：

```
<summary>
Scope: X earlier messages (user=N, assistant=N, tool=N)
Recent user requests:
  - 請求內容1
  - 請求內容2
Key files referenced: py, js, json
Key timeline:
  - [role] 內容摘要
  - [role] 內容摘要
</summary>
```

#### `compact(messages: list) -> list`
執行壓縮，返回新的消息列表

## 執行測試

```bash
cd C:/butler_sumo/tools/mini_coding_agent
python test_compactor.py
```

## 輸出範例

### 壓縮前 (7 條消息)
```
[user] 幫我寫一個 Python 程式
[assistant] 好的，這是一個簡單的 Python 程式...
[tool] 檔案已建立：demo.py
[user] 再幫我加一個功能
[assistant] 已加入新功能
[user] 測試一下
[assistant] 測試通過
```

### 壓縮後 (3 條消息)
```
[system] <summary>
Scope: 5 earlier messages (user=3, assistant=2, tool=1)
Recent user requests:
  - 幫我寫一個 Python 程式
  - 再幫我加一個功能
Key files referenced: demo.py
Key timeline:
  - [user] 幫我寫一個 Python 程式
  - [assistant] 好的，這是一個簡單的...
  - ...
</summary>
[user] 測試一下
[assistant] 測試通過
```

## License

MIT
