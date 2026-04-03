"""
history_manager.py - Conversation History Manager with LLM-based Summarization

自主管理的對話歷史，自動用 MiniMax API 做摘要壓縮。
"""

import os
import json
from typing import List, Dict, Tuple, Optional


class ConversationHistoryManager:
    """
    自主管理的對話歷史，自動壓縮

    Features:
    - 維護對話歷史 (user, assistant) tuples
    - 超過閾值時自動用 MiniMax API 做摘要
    - 保留最近 N 條對話不被壓縮
    """

    def __init__(
        self,
        max_history: int = 20,
        max_tokens: int = 10000,
        preserve_recent: int = 4
    ):
        """
        Args:
            max_history: 最大對話輪數，超過後觸發壓縮
            max_tokens: 最大 token 數，超過後觸發壓縮
            preserve_recent: 壓縮時保留最近 N 輪對話
        """
        self.history: List[Tuple[str, str]] = []  # [(user_msg, assistant_msg), ...]
        self.max_history = max_history
        self.max_tokens = max_tokens
        self.preserve_recent = preserve_recent
        self.compact_count = 0
        self.summary_count = 0

    def add_turn(self, user_msg: str, assistant_msg: str = "") -> None:
        """新增一輪對話"""
        self.history.append((user_msg, assistant_msg))

    def update_last_assistant(self, assistant_msg: str) -> None:
        """更新最後一輪的 assistant 回應"""
        if self.history:
            user_msg, _ = self.history[-1]
            self.history[-1] = (user_msg, assistant_msg)

    def estimate_tokens(self, text: str) -> int:
        """估算 token 數量（簡單估算：文字長度 / 4 + 1）"""
        if not text:
            return 0
        return len(text) // 4 + 1

    def should_compact(self) -> bool:
        """判斷是否需要壓縮"""
        # 超過最大歷史輪數
        if len(self.history) > self.max_history:
            return True

        # 超過最大 token 數
        total_tokens = sum(
            self.estimate_tokens(u) + self.estimate_tokens(a)
            for u, a in self.history
        )
        return total_tokens > self.max_tokens

    def _format_history_for_summary(self, history: List[Tuple[str, str]]) -> str:
        """將歷史格式化成摘要 prompt 的輸入"""
        lines = []
        for i, (user_msg, assistant_msg) in enumerate(history, 1):
            lines.append(f"--- 第 {i} 輪對話 ---")
            lines.append(f"用戶: {user_msg}")
            if assistant_msg:
                lines.append(f"助理: {assistant_msg}")
            lines.append("")
        return "\n".join(lines)

    def compact(self, llm_provider) -> bool:
        """
        用 MiniMax API 自動摘要壓縮歷史

        Args:
            llm_provider: LLMProvider 實例（如 MiniMaxProvider）

        Returns:
            True if compaction was performed, False otherwise
        """
        if len(self.history) <= self.preserve_recent:
            return False

        # 1. 取出要摘要的歷史（除了最近 N 條）
        to_summarize = self.history[:-self.preserve_recent]
        if not to_summarize:
            return False

        # 2. 組成摘要 prompt
        history_text = self._format_history_for_summary(to_summarize)
        summary_prompt = f"""請簡潔摘要以下對話內容，保留所有關鍵資訊（200字以內）：

{history_text}

請用繁體中文回覆，格式：
【對話摘要】<摘要內容>
【關鍵資訊】<提取的重要資訊，如檔案名稱、决策、任務等>"""

        # 3. 呼叫 MiniMax API
        if hasattr(llm_provider, 'summarize'):
            summary_response = llm_provider.summarize(summary_prompt)
        else:
            # Fallback: 如果 provider 沒有 summarize 方法，用 complete
            response = llm_provider.complete(
                messages=[{"role": "user", "content": summary_prompt}],
                tools=None
            )
            summary_response = response.get("content", "")

        # 4. 將舊歷史替換為單一摘要訊息，保留最近的歷史
        self.history = [(f"[歷史摘要 #{self.summary_count + 1}] {summary_response}", "")] + list(self.history[-self.preserve_recent:])
        self.compact_count += 1
        self.summary_count += 1

        print(f"[HistoryManager] 壓縮完成！已壓縮 {len(to_summarize)} 輪對話為摘要 (compaction #{self.compact_count})")
        return True

    def get_recent_history(self, n: int = 10) -> List[Tuple[str, str]]:
        """取得最近的 N 輪對話"""
        return self.history[-n:] if n > 0 else self.history

    def get_all_history(self) -> List[Tuple[str, str]]:
        """取得所有歷史"""
        return self.history.copy()

    def get_history_for_llm(self, n: int = 10) -> List[Dict[str, str]]:
        """
        取得最近 N 輪對話，格式化成 LLM 訊息列表

        Returns:
            List of {"role": str, "content": str} messages
        """
        recent = self.get_recent_history(n)
        messages = []
        for user_msg, assistant_msg in recent:
            messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})
        return messages

    def clear(self) -> None:
        """清除所有歷史"""
        self.history.clear()
        self.compact_count = 0
        self.summary_count = 0

    def get_stats(self) -> Dict:
        """取得統計資訊"""
        total_tokens = sum(
            self.estimate_tokens(u) + self.estimate_tokens(a)
            for u, a in self.history
        )
        return {
            "total_turns": len(self.history),
            "estimated_tokens": total_tokens,
            "compact_count": self.compact_count,
            "summary_count": self.summary_count,
            "should_compact": self.should_compact()
        }


def create_history_manager(
    max_history: int = 20,
    max_tokens: int = 10000,
    preserve_recent: int = 4
) -> ConversationHistoryManager:
    """工廠函式：建立 ConversationHistoryManager"""
    return ConversationHistoryManager(
        max_history=max_history,
        max_tokens=max_tokens,
        preserve_recent=preserve_recent
    )


if __name__ == "__main__":
    # 簡單測試
    manager = ConversationHistoryManager(max_history=5, preserve_recent=2)

    # 加入一些測試對話
    manager.add_turn("幫我寫一個 hello world 程式", "好的，這是 Python 的 hello world：\nprint('Hello, World!')")
    manager.add_turn("再幫我寫一個加法程式", "好的，這是加法程式：\na = 1\nb = 2\nprint(a + b)")
    manager.add_turn("測試一下", "測試通過！")

    print("History turns:", len(manager.history))
    print("Should compact:", manager.should_compact())
    print("\nHistory:")
    for i, (u, a) in enumerate(manager.history):
        print(f"{i}: User: {u[:30]}... | Assistant: {a[:30]}...")
