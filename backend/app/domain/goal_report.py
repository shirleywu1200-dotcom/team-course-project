"""目標回報（todo 9.10；spec 5.3a〈AI-04〉、5.13「目標回報」）：讀出產生草稿與重新對帳所需的資料。

統計與 GET /goals/{id}/stats 同一份計算（goal_stats.load＋summarize），payload 的 tasks 取自同一母體。
產生與讀取時都用這裡的 payload：產生時送 AI，讀取時拿存下的草稿對目前的 payload 重跑 R3（第 5 點）。
"""

from dataclasses import dataclass

from sqlalchemy import Connection

from app.db.repo import projects_repo
from app.domain import ai04, goal_stats


@dataclass(frozen=True)
class ReportInput:
    payload: dict            # 送給 AI-04 的內容
    excluded_private: int    # 母體中私人範圍的件數：只進統計，不列標題
    sendable: bool           # 依規則可呼叫 AI：有關聯，且目標沒有綁私人專案（spec 5.13 第 4、7 點）


def collect(conn: Connection, goal_id: int) -> ReportInput:
    goal, rows, counts = goal_stats.load(conn, goal_id)   # 目標不存在：NOT_FOUND
    stats = goal_stats.summarize(goal, rows, counts)
    private_goal = goal["project_id"] is not None \
        and projects_repo.get(conn, goal["project_id"])["scope"] == "private"   # 以送出當下判定（Q6，#92）
    return ReportInput(payload=ai04.build_payload(goal, stats, rows),
                       excluded_private=sum(1 for r in rows if r["scope"] == "private"),
                       sendable=stats["linked"] > 0 and not private_goal)
