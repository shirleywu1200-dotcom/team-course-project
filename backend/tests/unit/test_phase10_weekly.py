"""Phase 10 第一段：週報資料彙整（10.1）、退路事件清單、R4 對帳（10.3）。

只測已裁定的行為（issue #18 裁定 A～F、5、6）。#18 的 G1～G8 待裁定，裁定後再補。
本週 = 2026-11-09（一）～11-15（日），下週 = 11-16～11-22。「今天」固定 2026-11-11。
"""

import json
from datetime import date, datetime

import pytest

from app.clock import TZ
from app.domain import weekly_report
from app.errors import DomainError

WEEK = date(2026, 11, 9)
MARK = "機密標記XYZ"   # 種子把它放進不該外流的欄位，輸出裡不能出現

TS = "'2026-11-01T09:00+08:00'"
DATA = f"""
INSERT INTO projects (id, name, scope, audience, created_at, updated_at) VALUES
  (1, '工作專案', 'work', 'manager', {TS}, {TS}),
  (2, '私人專案', 'private', 'none', {TS}, {TS});

INSERT INTO tasks (id, project_id, title, owner_name, scope, start_date, orig_due, latest_due,
                   status, done_date, blocked, done_when, version, created_at, updated_at) VALUES
  (1,  1,    '本週完成',       '我',   'work',    '2026-11-01', '2026-11-10', '2026-11-10', 'done',  '2026-11-10', false, '{MARK}', 2, {TS}, {TS}),
  (2,  1,    '上週日完成',     '我',   'work',    '2026-11-01', '2026-11-08', '2026-11-08', 'done',  '2026-11-08', false, '', 2, {TS}, {TS}),
  (3,  1,    '下週一完成',     '我',   'work',    '2026-11-01', '2026-11-16', '2026-11-16', 'done',  '2026-11-16', false, '', 2, {TS}, {TS}),
  (4,  1,    '延期兩次',       '小薇', 'work',    '2026-11-01', '2026-11-12', '2026-11-15', 'doing', NULL, false, '', 4, {TS}, {TS}),
  (5,  1,    '邊界延期',       '阿德', 'work',    '2026-11-01', '2026-11-12', '2026-11-30', 'todo',  NULL, false, '', 4, {TS}, {TS}),
  (6,  1,    '私人延期',       '我',   'private', '2026-11-01', '2026-11-12', '2026-11-18', 'todo',  NULL, false, '', 2, {TS}, {TS}),
  (7,  1,    '私人完成',       '我',   'private', '2026-11-01', '2026-11-12', '2026-11-12', 'done',  '2026-11-12', false, '', 2, {TS}, {TS}),
  (8,  1,    '私人不相干',     '我',   'private', '2026-11-01', '2026-12-30', '2026-12-30', 'todo',  NULL, false, '', 1, {TS}, {TS}),
  (9,  2,    '私人專案的工作', '我',   'work',    '2026-11-01', '2026-11-20', '2026-11-20', 'todo',  NULL, false, '', 1, {TS}, {TS}),
  (10, 1,    '卡住',           '我',   'work',    '2026-11-01', '2026-12-30', '2026-12-30', 'todo',  NULL, true,  '', 2, {TS}, {TS}),
  (11, 1,    '下週到期已完成', '我',   'work',    '2026-11-01', '2026-11-18', '2026-11-18', 'done',  '2026-11-05', false, '', 2, {TS}, {TS}),
  (12, 1,    '下下週一到期',   '我',   'work',    '2026-11-01', '2026-11-23', '2026-11-23', 'todo',  NULL, false, '', 1, {TS}, {TS}),
  (13, 1,    '下週一到期',     '我',   'work',    '2026-11-01', '2026-11-16', '2026-11-16', 'doing', NULL, false, '', 1, {TS}, {TS}),
  (14, 1,    '下週日到期',     '我',   'work',    '2026-11-01', '2026-11-22', '2026-11-22', 'todo',  NULL, false, '', 1, {TS}, {TS}),
  (15, NULL, '單點延期',       '我',   'work',    '2026-11-01', '2026-11-12', '2026-12-13', 'todo',  NULL, false, '', 2, {TS}, {TS}),
  (16, 1,    '只有候選',       '我',   'work',    '2026-11-01', '2026-11-12', '2026-12-12', 'todo',  NULL, false, '', 1, {TS}, {TS}),
  (17, 1,    '只有基準與註記', '我',   'work',    '2026-11-01', '2026-11-14', '2026-12-14', 'todo',  NULL, false, '', 3, {TS}, {TS});

INSERT INTO sources (id, channel, speaker, excerpt, excerpt_hash, received_at, expires_at) VALUES
  (1, 'paste', '阿德', '{MARK} 原句', 'h1', {TS}, '2026-12-31T00:00+08:00');

INSERT INTO candidates (id, source_id, kind, certainty, task_id, proposed, note, state, created_at) VALUES
  (1, 1, 'delay', 'sure', 16, '{{"new_due": "2026-11-20", "x": "{MARK}"}}', '{MARK}', 'open', {TS});

INSERT INTO events (id, ts, project_id, task_id, task_title, kind, field, from_value, to_value, origin,
                    delta_days, mark, mine, reason, note, source_id, extra, ref_event_id) VALUES
  (100, '2026-11-09T09:00+08:00', 1, 1, '本週完成', 'status', 'status', 'todo', 'doing', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (101, '2026-11-10T09:00+08:00', 1, 1, '本週完成', 'status', 'blocked', 'false', 'true', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (102, '2026-11-10T18:00+08:00', 1, 1, '本週完成', 'status', 'status', 'doing', 'done', 'manual', NULL, NULL, true, NULL, '{MARK}', NULL, '{{"done_date": "2026-11-10", "x": "{MARK}"}}', NULL),
  (103, '2026-11-08T18:00+08:00', 1, 2, '上週日完成', 'status', 'status', 'todo', 'done', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (104, '2026-11-12T18:00+08:00', 1, 7, '私人完成', 'status', 'status', 'todo', 'done', 'manual', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (110, '2026-11-10T10:00+08:00', 1, 4, '延期兩次', 'due', 'latest_due', '2026-11-12', '2026-11-14', 'candidate', 2, 'worse', false, 'underestimated', '{MARK}', 1, NULL, NULL),
  (111, '2026-11-15T23:30+08:00', 1, 4, '延期兩次', 'due', 'latest_due', '2026-11-14', '2026-11-16', 'bulk', 2, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (112, '2026-11-15T23:40+08:00', 1, 4, '延期兩次', 'due', 'latest_due', '2026-11-16', '2026-11-15', 'manual', -1, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (120, '2026-11-08T23:50+08:00', 1, 5, '邊界延期', 'due', 'latest_due', '2026-11-12', '2026-11-20', 'manual', 8, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (121, '2026-11-09T00:10+08:00', 1, 5, '邊界延期', 'due', 'latest_due', '2026-11-20', '2026-11-25', 'manual', 5, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (122, '2026-11-15T16:10Z',      1, 5, '邊界延期', 'due', 'latest_due', '2026-11-25', '2026-11-30', 'manual', 5, NULL, false, NULL, NULL, NULL, NULL, NULL),
  (130, '2026-11-11T10:00+08:00', 1, 6, '私人延期', 'due', 'latest_due', '2026-11-12', '2026-11-18', 'manual', 6, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (140, '2026-11-11T10:00+08:00', NULL, 15, '單點延期', 'due', 'latest_due', '2026-11-12', '2026-12-13', 'manual', 31, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (150, '2026-11-02T10:00+08:00', 1, 17, '只有基準與註記', 'due', 'latest_due', '2026-11-14', '2026-12-14', 'manual', 30, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (151, '2026-11-10T10:00+08:00', 1, 17, '只有基準與註記', 'baseline', 'orig_due', '2026-11-12', '2026-11-14', 'baseline_correction', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL),
  (152, '2026-11-10T11:00+08:00', 1, 17, '只有基準與註記', 'annotation', 'mark', NULL, 'worse', 'manual', NULL, 'worse', true, NULL, NULL, NULL, NULL, 150);
"""

DONE_KEYS = {"task_id", "title", "owner", "done_date", "event_id"}
DELAY_KEYS = {"task_id", "title", "owner", "orig_due", "latest_due", "event_ids"}
NEXT_KEYS = {"task_id", "title", "owner", "latest_due", "blocked"}


@pytest.fixture
def week(db, seed):
    seed(DATA)
    return db.run(lambda c: weekly_report.collect(c, WEEK))


def ids(items):
    return [i["task_id"] for i in items]


# 1、週一限制（#18 裁定 5）
@pytest.mark.parametrize("bad", [date(2026, 11, 8), date(2026, 11, 10)])
def test_week_start_must_be_monday(db, bad):
    with pytest.raises(DomainError) as e:
        db.run(lambda c: weekly_report.collect(c, bad))
    assert e.value.code == "VALIDATION_ERROR" and e.value.details == {"fields": ["week_start"]}


def test_next_monday_is_accepted(db):
    assert db.run(lambda c: weekly_report.collect(c, date(2026, 11, 16))).done == []


# 2、3、本週完成（裁定 C、F）
def test_done_by_done_date_within_week_with_its_done_event(week):
    assert ids(week.done) == [1]   # 11/08、11/16 完成的不算；私人的 7 排除
    assert week.done[0] == {"task_id": 1, "title": "本週完成", "owner": "我",
                            "done_date": date(2026, 11, 10), "event_id": 102}   # 不是 doing 或卡住那筆 status 事件


# 4、5、6、延期（裁定 D）
def test_delay_by_week_due_events_with_positive_delta(week):
    assert ids(week.delay) == [4, 5, 15]   # 單點任務也列入；私人的 6 排除；只有候選、基準或註記的不列入


def test_delay_groups_events_and_skips_advances(week):
    item = next(i for i in week.delay if i["task_id"] == 4)
    assert item["event_ids"] == [110, 111]   # 112 是提前，不算；整批、候選、非我的任務都算


def test_delay_week_boundaries_use_taipei_date(week):
    item = next(i for i in week.delay if i["task_id"] == 5)
    # 120：11/08 23:50 不算；121：11/09 00:10 算（UTC 仍是 11/08）；122：UTC 11/15 16:10 ＝台北 11/16 00:10，不算
    assert item["event_ids"] == [121]


# 7、原訂取目前值（AC-25）
def test_delay_uses_current_orig_and_latest_due(week):
    item = next(i for i in week.delay if i["task_id"] == 4)
    assert (item["orig_due"], item["latest_due"]) == (date(2026, 11, 12), date(2026, 11, 15))


# 8、下週重點（裁定 E）
def test_next_week_due_or_blocked_unfinished(week):
    # 13、14：下週一、下週日到期；9：私人專案底下的工作任務；10：卡住（期限在更後面）
    # 11 已完成、12 下下週一、6 私人：不列入
    assert sorted(ids(week.next)) == [9, 10, 13, 14]
    assert next(i for i in week.next if i["task_id"] == 10)["blocked"] is True


# 9、10、11、私人範圍（AC-48、裁定 A、B）
def test_private_tasks_never_appear(week):
    all_ids = ids(week.done) + ids(week.delay) + ids(week.next)
    assert not {6, 7, 8} & set(all_ids)


def test_excluded_private_counts_tasks_once(week):
    # 6（延期且下週到期，算 1）＋ 7（完成）＝ 2；8 不會進任何一段，不算
    assert week.excluded_private == 2


def test_switching_a_task_to_private_moves_it_into_the_count(db, seed):
    seed(DATA + "UPDATE tasks SET scope = 'private' WHERE id = 4;")
    w = db.run(lambda c: weekly_report.collect(c, WEEK))
    assert 4 not in ids(w.delay) and w.excluded_private == 3


# 13、輸出只有白名單的鍵，不含原文、備註、原因、註記
def test_items_have_exact_whitelisted_keys(week):
    assert all(set(i) == DONE_KEYS for i in week.done)
    assert all(set(i) == DELAY_KEYS for i in week.delay)
    assert all(set(i) == NEXT_KEYS for i in week.next)


def test_output_carries_no_marked_text(week):
    dumped = json.dumps([week.done, week.delay, week.next, week.excluded_private], default=str, ensure_ascii=False)
    assert MARK not in dumped and "underestimated" not in dumped and "worse" not in dumped


# 時鐘在別週，結果不變（區間只由 week_start 決定）
def test_result_independent_of_today(db, seed, clock):
    seed(DATA)
    before = db.run(lambda c: weekly_report.collect(c, WEEK))
    clock.set(datetime(2026, 11, 25, 10, 0, tzinfo=TZ))
    assert db.run(lambda c: weekly_report.collect(c, WEEK)) == before


# 18、空的一週
def test_empty_week(db):
    w = db.run(lambda c: weekly_report.collect(c, WEEK))
    assert (w.done, w.delay, w.next, w.excluded_private) == ([], [], [], 0)
    assert weekly_report.fallback_items(w) == []
    assert weekly_report.reconcile([], w) is True


# 14、退路事件清單（spec 5.14、#18 裁定 4）
def test_fallback_items_list_every_event_in_fixed_order(week):
    items = weekly_report.fallback_items(week)
    assert all(set(i) == {"section", "task_id", "event_id"} for i in items)
    assert [i for i in items if i["section"] == "done"] == [{"section": "done", "task_id": 1, "event_id": 102}]
    assert [(i["task_id"], i["event_id"]) for i in items if i["section"] == "delay"] == \
        [(4, 110), (4, 111), (5, 121), (15, 140)]
    assert all(i["event_id"] is None for i in items if i["section"] == "next")
    assert weekly_report.fallback_items(week) == items   # 重算結果相同


# 15～17、R4 對帳（FR-RPT-03、AC-49）
def test_reconcile_accepts_items_matching_week_events(week):
    ai_items = [{"section": "done", "task_id": 1, "event_id": 102},
                {"section": "delay", "task_id": 4, "event_id": 111},
                {"section": "delay", "task_id": 15, "event_id": 140}]
    assert weekly_report.reconcile(ai_items, week) is True


@pytest.mark.parametrize("bad", [
    {"section": "delay", "task_id": 5, "event_id": 120},    # 本週以外的事件
    {"section": "delay", "task_id": 4, "event_id": 999},    # 歷程中找不到的事件（AC-49）
    {"section": "done", "task_id": 1, "event_id": 104},     # 別的任務的完成事件
    {"section": "delay", "task_id": 6, "event_id": 130},    # 私人任務的事件
    {"section": "done", "task_id": 1, "event_id": None},    # 完成沒附事件
    {"section": "delay", "task_id": 4, "event_id": None},   # 延期沒附事件
    {"section": "done", "task_id": 4, "event_id": 110},     # 種類錯置：完成引用延期事件
    {"section": "delay", "task_id": 1, "event_id": 102},    # 種類錯置：延期引用完成事件
    {"section": "delay", "task_id": 4, "event_id": 112},    # 同週的提前事件不是延期
])
def test_reconcile_rejects_items_not_backed_by_week_events(week, bad):
    ok = {"section": "done", "task_id": 1, "event_id": 102}
    assert weekly_report.reconcile([ok, bad], week) is False


def test_reconcile_rejects_items_when_week_is_empty(db):
    w = db.run(lambda c: weekly_report.collect(c, WEEK))
    assert weekly_report.reconcile([{"section": "done", "task_id": 1, "event_id": 102}], w) is False
