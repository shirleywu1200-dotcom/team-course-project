"""目標統計、判讀與矩陣（FR-GOL-04、05；spec 5.13；AC-46；#47 G2、B3、B4）。

判讀由程式規則計算，非 AI。summarize 與 judge 是純函式，不碰資料庫；stats、matrix 負責讀資料後交給它們。
"""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Connection

from app.db.repo import goal_links_repo, goals_repo

MIN_SAMPLE = 5                                   # 〔假設〕門檻，G2 驗證（FR-GOL-05）
LEVELS = ("high", "mid", "low")                  # 並列時依此順序列出
LABEL = {"high": "高", "mid": "中", "low": "低"}


def _ratio(numerator: int, denominator: int, places: int) -> Decimal:
    """以 Decimal 相除後四捨五入（不經浮點數，也不用 Python round 的銀行家捨入）。"""
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def _avg(values: list[int]) -> float | None:
    return float(_ratio(sum(values), len(values), 1)) if values else None


def energy_distribution(rows: list[dict]) -> dict:
    return {level: sum(1 for r in rows if r["energy"] == level) for level in LEVELS}


def judge(energy: dict, energy_plan: str, linked: int) -> tuple[str | None, str]:
    """回傳 (judgement, judgement_note)。"""
    if linked < MIN_SAMPLE:
        return None, f"樣本 {linked} 筆，不到 {MIN_SAMPLE} 筆，只顯示不下結論"
    top = max(energy.values())
    main = [level for level in LEVELS if energy[level] == top]
    if len(main) > 1:                            # 並列不替使用者挑（G2）
        return "建議檢視", "主要精力並列：" + "、".join(LABEL[level] for level in main)
    if main[0] == energy_plan:
        return "一致", f"主要精力為{LABEL[main[0]]}，與預期相同"
    return "建議檢視", f"主要精力為{LABEL[main[0]]}，預期為{LABEL[energy_plan]}"


def _pct(numerator: int, denominator: int) -> int | None:
    return None if denominator == 0 else min(100, int(_ratio(numerator * 100, denominator, 0)))


def progress(goal: dict, linked: int, project_counts: tuple[int, int] | None) -> dict | None:
    if goal["type"] == "growth":
        return {"text": f"{linked} ／ {goal['target']} 件完成事件", "pct": _pct(linked, goal["target"])}
    if goal["type"] == "expectation":
        done, total = project_counts
        return {"text": f"{done} ／ {total} 件專案任務完成", "pct": _pct(done, total)}
    return None                                  # time：只顯示統計（B3）


def summarize(goal: dict, rows: list[dict], project_counts: tuple[int, int] | None) -> dict:
    """由母體逐筆資料算出 spec 5.13 的 stats 輸出。"""
    linked = len(rows)
    energy = energy_distribution(rows)
    judgement, note = judge(energy, goal["energy_plan"], linked)
    return {
        "progress": progress(goal, linked, project_counts),
        "linked": linked,
        "avg_actual": _avg([r["actual_stars"] for r in rows]),
        "avg_expected": _avg([r["expected_stars"] for r in rows]),
        "overdue_count": sum(1 for r in rows if r["overdue_days"] > 0),
        "energy": energy,
        "energy_plan": goal["energy_plan"],
        "min_sample": MIN_SAMPLE,
        "judgement": judgement,
        "judgement_note": note,
    }


def stats(conn: Connection, goal_id: int) -> dict:
    goal = goals_repo.get(conn, goal_id)          # 不存在：NOT_FOUND；封存照常可查
    counts = goal_links_repo.project_progress(conn, goal["project_id"]) if goal["type"] == "expectation" else None
    return summarize(goal, goal_links_repo.linked_rows(conn, goal_id), counts)


def matrix(conn: Connection) -> list[dict]:
    """每個未封存目標一列；精力與件數的母體與 stats 相同。"""
    rows = goal_links_repo.linked_rows(conn)
    items = []
    for goal in goals_repo.list_all(conn, include_archived=False):
        mine = [r for r in rows if r["goal_id"] == goal["id"]]
        items.append({"goal_id": goal["id"], "title": goal["title"], "energy_plan": goal["energy_plan"],
                      "energy": energy_distribution(mine), "linked": len(mine)})
    return items
