"""13.8 埋點檢查（資料面）：spec 1.3 衡量值的查詢能在實際 DDL 上算出正確數字。

QC-2 另以真實試用資料驗算（13.8 驗算部分），不在此。
"""

from decimal import Decimal

from app.db.repo import metrics_repo
from tests.unit.seeds import BASE, RUBRIC

DATA = BASE + RUBRIC + """
INSERT INTO sources (id, channel, speaker, excerpt_hash, received_at, expires_at)
  VALUES (1, 'paste', '阿德', 'h1', now(), now());
INSERT INTO candidates (source_id, kind, certainty, state, decided_at, created_at) VALUES
  (1, 'delay', 'sure', 'confirmed', '2026-11-11T18:00+08:00', now()),
  (1, 'done',  'sure', 'confirmed', '2026-11-11T18:04+08:00', now()),
  (1, 'stuck', 'sure', 'ignored',   '2026-11-11T18:03+08:00', now()),
  (1, 'delay', 'sure', 'open',      NULL, now());
INSERT INTO events (id, ts, task_id, task_title, kind, field, origin, delta_days, mark, mine) VALUES
  (1, now(), 4, 'x', 'due', 'latest_due', 'manual', 2, 'worse', true),
  (2, now(), 5, 'x', 'due', 'latest_due', 'manual', 3, NULL, true),
  (3, now(), 6, 'x', 'due', 'latest_due', 'manual', 1, NULL, true),
  (4, now(), 2, 'x', 'due', 'latest_due', 'manual', 4, NULL, false);
INSERT INTO events (id, ts, task_id, task_title, kind, field, origin, mark, mine, ref_event_id) VALUES
  (5, now(), 5, 'x', 'annotation', 'mark', 'manual', 'none', true, 2);
INSERT INTO completion_feedback (task_id, actual_stars, energy, overdue_days, rubric_id, created_at)
  VALUES (1, 4, 'mid', 0, 1, now());
UPDATE tasks SET status = 'done', done_date = '2026-11-11' WHERE id = 7;
"""


def test_metric3_candidate_confirm_rate(db, seed):
    seed(DATA)
    r = db.run(metrics_repo.candidate_confirm_rate)
    assert (r["numerator"], r["denominator"]) == (2, 3)


def test_metric4_mark_completion_rate_uses_effective_mark(db, seed):
    seed(DATA)
    r = db.run(metrics_repo.mark_completion_rate)
    assert (r["numerator"], r["denominator"]) == (2, 3)


def test_metric5_feedback_fill_rate(db, seed):
    seed(DATA)
    r = db.run(metrics_repo.feedback_fill_rate)
    assert (r["numerator"], r["denominator"]) == (1, 2)


def test_metric2_daily_span_approximation(db, seed):
    seed(DATA)
    rows = db.run(metrics_repo.daily_confirm_span_minutes)
    assert len(rows) == 1 and rows[0]["span_min"] == Decimal("4.0") and rows[0]["decisions"] == 3


def test_empty_database_gives_null_rates(db):
    for fn in (metrics_repo.candidate_confirm_rate, metrics_repo.mark_completion_rate,
               metrics_repo.feedback_fill_rate):
        assert db.run(fn)["rate"] is None
