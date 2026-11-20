"""目標回報（todo 9.10；spec 5.3a〈AI-04〉）：讀出產生草稿所需的資料。

統計與 GET /goals/{id}/stats 同一份計算（goal_stats.load＋summarize），payload 的 tasks 取自同一母體。
端點、存檔與 R3 對帳等 #47 9.10 裁定後再加。
"""

from dataclasses import dataclass

from sqlalchemy import Connection

from app.domain import ai04, goal_stats


@dataclass(frozen=True)
class ReportInput:
    payload: dict            # 送給 AI-04 的內容
    excluded_private: int    # 母體中私人範圍的件數：只進統計，不列標題


def collect(conn: Connection, goal_id: int) -> ReportInput:
    goal, rows, counts = goal_stats.load(conn, goal_id)   # 目標不存在：NOT_FOUND
    stats = goal_stats.summarize(goal, rows, counts)
    return ReportInput(payload=ai04.build_payload(goal, stats, rows),
                       excluded_private=sum(1 for r in rows if r["scope"] == "private"))
