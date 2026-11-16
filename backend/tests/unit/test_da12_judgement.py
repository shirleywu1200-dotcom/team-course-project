"""DA-12 時間管理判讀（FR-MRK-07、AC-64；#15 產品負責人裁定，編號經 PR #27 確認）。

樣本＝變好＋變差次數；不足 min_sample 不下結論。精力洞察的分母是精力分布四格合計（含 not_done），
某一級嚴格大於一半才加集中提示。判讀由程式規則計算，不用 AI。
"""

from tests.unit.seeds import BASE

STATS = "/api/v1/stats/time-management"
INSUFFICIENT = "樣本 {n} 筆，不到 5 筆，只顯示不下結論"


def seed_marks(better: int, worse: list[str | None], extra_sql: str = "") -> str:
    """每筆註記各放在一個新任務上。worse 的每個元素是該任務的完成精力（None＝尚未完成）。"""
    rows, events, feedback = [], [], []
    tid = 100
    for kind, energies in (("better", [None] * better), ("worse", worse)):
        for energy in energies:
            tid += 1
            delta = -1 if kind == "better" else 2
            status, done = ("done", "'2026-11-10'") if energy else ("todo", "NULL")
            rows.append(f"({tid}, 1, 't{tid}', '我', 'work', '2026-11-01', '2026-11-20', '2026-11-20', "
                        f"'{status}', {done}, now(), now())")
            events.append(f"(now(), 1, {tid}, 't{tid}', 'due', 'latest_due', 'manual', {delta}, '{kind}', true)")
            if energy:
                feedback.append(f"({tid}, 3, '{energy}', 0, 1, now())")
    sql = BASE
    if rows:
        sql += ("INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due, "
                "status, done_date, created_at, updated_at) VALUES " + ",\n".join(rows) + ";\n")
        sql += ("INSERT INTO events (ts, project_id, task_id, task_title, kind, field, origin, delta_days, mark, mine) "
                "VALUES " + ",\n".join(events) + ";\n")
    if feedback:
        sql += ("INSERT INTO completion_feedback (task_id, actual_stars, energy, overdue_days, rubric_id, created_at) "
                "VALUES " + ",\n".join(feedback) + ";\n")
    return sql + extra_sql


def stats(client, seed, better, worse, extra_sql=""):
    seed(seed_marks(better, worse, extra_sql))
    return client.get(STATS).json()


# ---------- AC-64 的 5 個情境 ----------

def test_ac64_insufficient_sample(client, seed):
    s = stats(client, seed, 1, [None, None, None])
    assert s["judgement"] is None and s["judgement_note"] == INSUFFICIENT.format(n=4)


def test_ac64_leaning_better(client, seed):
    s = stats(client, seed, 4, [None, None])
    assert s["judgement"] == "時間管理偏向變好"
    assert s["judgement_note"] == "變好 4 次、變差 2 次。"


def test_ac64_leaning_worse_with_low_energy_concentration(client, seed):
    s = stats(client, seed, 2, ["low", "low", "mid"])
    assert s["judgement"] == "偏向變差，建議檢視"
    assert s["judgement_note"] == "變好 2 次、變差 3 次。變差多集中在低精力任務。"


def test_ac64_exactly_half_is_not_concentration(client, seed):
    s = stats(client, seed, 1, ["low", "low", "mid", "mid"])
    assert s["judgement"] == "偏向變差，建議檢視"
    assert s["judgement_note"] == "變好 1 次、變差 4 次。"


def test_ac64_even(client, seed):
    s = stats(client, seed, 3, [None, None, None])
    assert s["judgement"] == "持平" and s["judgement_note"] == "變好 3 次、變差 3 次。"


# ---------- 規則邊界 ----------

def test_sample_of_exactly_five_gets_a_judgement(client, seed):
    s = stats(client, seed, 3, [None, None])
    assert s["judgement"] == "時間管理偏向變好"


def test_not_done_is_in_the_denominator_but_never_a_level(client, seed):
    # 變差 4 個任務：未完成 3、高 1。高只佔 1/4；未完成佔多數也不出「集中」句
    s = stats(client, seed, 1, [None, None, None, "high"])
    assert s["judgement_note"] == "變好 1 次、變差 4 次。"


def test_high_energy_concentration(client, seed):
    s = stats(client, seed, 2, ["high", "high", "low"])
    assert s["judgement_note"] == "變好 2 次、變差 3 次。變差多集中在高精力任務。"


def test_no_worse_means_no_concentration_sentence(client, seed):
    s = stats(client, seed, 5, [])
    assert s["judgement"] == "時間管理偏向變好" and s["judgement_note"] == "變好 5 次、變差 0 次。"


def test_none_and_unmarked_do_not_count_toward_the_sample(client, seed):
    # 不計入與未註記不進樣本（FR-MRK-06）：變好 2、變差 2，另有 1 筆不計入、1 筆未註記 → 樣本 4
    extra = """
    INSERT INTO events (ts, project_id, task_id, task_title, kind, field, origin, delta_days, mark, mine) VALUES
      (now(), 1, 4, 'x', 'due', 'latest_due', 'manual', 1, 'none', true),
      (now(), 1, 5, 'x', 'due', 'latest_due', 'manual', 1, NULL, true);
    """
    s = stats(client, seed, 2, [None, None], extra)
    assert s["judgement"] is None and s["judgement_note"] == INSUFFICIENT.format(n=4)


def test_empty_stats_say_insufficient(client):
    s = client.get(STATS).json()
    assert s["judgement"] is None and s["judgement_note"] == INSUFFICIENT.format(n=0)


def test_openapi_declares_judgement_note(client):
    props = client.get("/api/v1/openapi.json").json()["components"]["schemas"]["TimeMgmtStatsOut"]["properties"]
    assert "judgement_note" in props
