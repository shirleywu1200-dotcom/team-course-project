"""AI-04 目標回報草稿的輸入格式（FR-GOL-06；spec 5.3a〈AI-04〉）。

格式以 spec 5.3a 為準（2026-11-18 #72、#73 定案；節點與 prompt 為 Dev-B 的 app/ai/nodes/ai04.py）。
格式要改時先改 spec，再改這個檔。
- 輸入只放白名單欄位：目標的類型、名稱、期間、預期精力；程式算好的彙總統計；工作範圍任務的 id、名稱、完成日。
- 不送逐筆的星數與精力（FR-AI-06）、目標定義、負責人、完成條件；私人任務只進統計數字、不列標題（資安規則 2）。
"""

NODE = "AI-04"


def build_payload(goal: dict, stats: dict, rows: list[dict]) -> dict:
    """goal：goals 列；stats：goal_stats.summarize 的輸出；rows：同一母體的逐筆資料。"""
    work = sorted((r for r in rows if r["scope"] == "work"), key=lambda r: (r["done_date"], r["task_id"]),
                  reverse=True)
    return {
        "goal": {"type": goal["type"], "title": goal["title"], "period": goal["period"],
                 "energy_plan": goal["energy_plan"]},
        "stats": {
            "linked": stats["linked"], "avg_actual": stats["avg_actual"], "avg_expected": stats["avg_expected"],
            "overdue_count": stats["overdue_count"], "energy": dict(stats["energy"]),
            "progress_pct": (stats["progress"] or {}).get("pct"), "judgement": stats["judgement"],
        },
        "tasks": [{"task_id": r["task_id"], "title": r["title"], "done_date": r["done_date"].isoformat()}
                  for r in work],
    }
