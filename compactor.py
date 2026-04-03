"""
三層記憶壓縮系統：Compression + Pruning + Summarization
"""

import re
from typing import Any


class Compactor:
    """三層記憶壓縮：Compression + Pruning + Summarization"""

    def __init__(self, preserve_recent: int = 4, max_tokens: int = 10000):
        self.preserve_recent = preserve_recent  # 保留最近 N 條
        self.max_tokens = max_tokens  # 觸發閾值

    def estimate_tokens(self, text: str) -> int:
        """
        第一層：Compression - 估算 token 數量
        簡單估算：文字長度 / 4 + 1
        """
        if not text:
            return 0
        return len(text) // 4 + 1

    def should_compact(self, messages: list) -> bool:
        """
        第二層：Pruning - 判斷是否需要壓縮
        超過 preserve_recent 條且總 token 超過 max_tokens
        """
        if len(messages) <= self.preserve_recent:
            return False

        total_tokens = sum(self.estimate_tokens(msg.get("content", "")) for msg in messages)
        return total_tokens > self.max_tokens

    def summarize_messages(self, messages: list) -> str:
        """
        第三層：Summarization - 結構化摘要
        輸出 <summary> 結構
        """
        # 統計角色數量
        role_counts = {"user": 0, "assistant": 0, "tool": 0}
        for msg in messages:
            role = msg.get("role", "unknown")
            if role in role_counts:
                role_counts[role] += 1

        scope = (
            f"{len(messages)} earlier messages "
            f"(user={role_counts['user']}, assistant={role_counts['assistant']}, tool={role_counts['tool']})"
        )

        # 取得最近 user 請求（最多3條，每條 Truncate 到 160 字）
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        recent_user_requests = []
        for msg in user_messages[-3:]:
            content = msg.get("content", "")
            if len(content) > 160:
                content = content[:160] + "..."
            if content:
                recent_user_requests.append(content)

        # 提取 Key files referenced（正則提取副檔名）
        all_content = " ".join(msg.get("content", "") for msg in messages)
        file_pattern = re.compile(r"\b[\w\-\.]+\.(py|js|ts|jsx|tsx|json|md|txt|cfg|yaml|yml|xml|html|css|sh|bat|ps1|sql|env|gitignore)\b")
        files = sorted(set(file_pattern.findall(all_content.lower())))

        # Key timeline（每條的 role + 內容摘要）
        timeline = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 摘要內容：取前 80 字
            if len(content) > 80:
                content = content[:80] + "..."
            timeline.append(f"[{role}] {content}")

        # 組裝結構化摘要
        lines = ["<summary>"]
        lines.append(f"Scope: {scope}")

        if recent_user_requests:
            lines.append("Recent user requests:")
            for req in recent_user_requests:
                lines.append(f"  - {req}")

        if files:
            lines.append(f"Key files referenced: {', '.join(files)}")

        if timeline:
            lines.append("Key timeline:")
            for item in timeline:
                lines.append(f"  - {item}")

        lines.append("</summary>")

        return "\n".join(lines)

    def compact(self, messages: list) -> list:
        """
        執行壓縮 - 返回壓縮後的消息列表
        保留最近 N 條原始消息，其餘轉換為一個 <summary> 結構化摘要訊息
        """
        if not messages:
            return []

        if len(messages) <= self.preserve_recent:
            return messages

        # 保留最近 N 條
        preserved = messages[-self.preserve_recent:]
        to_summarize = messages[:-self.preserve_recent]

        # 生成摘要
        summary_content = self.summarize_messages(to_summarize)

        # 建立摘要訊息
        summary_message = {
            "role": "system",
            "content": summary_content
        }

        return [summary_message] + preserved


# 方便直接呼叫
def compact_messages(messages: list, preserve_recent: int = 4, max_tokens: int = 10000) -> list:
    """
    快速函式：直接對消息列表進行壓縮
    """
    compactor = Compactor(preserve_recent=preserve_recent, max_tokens=max_tokens)
    if compactor.should_compact(messages):
        return compactor.compact(messages)
    return messages


if __name__ == "__main__":
    # 簡單測試
    test_messages = [
        {"role": "user", "content": "幫我寫一個 Python 程式"},
        {"role": "assistant", "content": "好的，這是一個簡單的 Python 程式..."},
        {"role": "tool", "content": "檔案已建立：demo.py"},
        {"role": "user", "content": "再幫我加一個功能"},
        {"role": "assistant", "content": "已加入新功能"},
        {"role": "user", "content": "測試一下"},
        {"role": "assistant", "content": "測試通過"},
    ]

    compactor = Compactor(preserve_recent=2)
    print("Should compact:", compactor.should_compact(test_messages))
    print("\nSummary:")
    print(compactor.summarize_messages(test_messages))
    print("\nCompact result:")
    result = compactor.compact(test_messages)
    for i, msg in enumerate(result):
        print(f"{i}: {msg['role']} -> {msg['content'][:50]}...")
