"""契約保護測試（todo 6.2）：凍結的函式簽名與錯誤碼清單一變動就紅。

要改這些契約，先依 todo 5.7 取得核可、改 spec／todo，再同步改這裡的期望值。
"""

import inspect
import re
from pathlib import Path

from app.ai.client import AIClient
from app.db.repo.tasks_repo import TaskRepo
from app.domain.due import adjust_due
from app.domain.events import write_event
from app.errors import ERROR_STATUS

SPEC = Path(__file__).resolve().parents[3] / "docs" / "spec.md"


def _params(fn) -> list[tuple[str, str]]:
    return [(p.name, p.kind.name) for p in inspect.signature(fn).parameters.values()]


def test_write_event_signature_is_frozen():
    assert _params(write_event) == [("session", "POSITIONAL_OR_KEYWORD"), ("fields", "VAR_KEYWORD")]


def test_adjust_due_signature_is_frozen():
    positional = ["session", "task_id", "new_due", "expected_version", "reason", "note", "mark", "defer_mark"]
    keyword_only = ["origin", "batch_id", "origin_ref", "source_id"]   # 後兩個為 DA-03 新增
    assert _params(adjust_due) == [(n, "POSITIONAL_OR_KEYWORD") for n in positional] + \
        [(n, "KEYWORD_ONLY") for n in keyword_only]
    defaults = {n: p.default for n, p in inspect.signature(adjust_due).parameters.items()}
    assert defaults["origin"] is inspect.Parameter.empty
    assert defaults["batch_id"] is defaults["origin_ref"] is defaults["source_id"] is None


def test_task_repo_get_for_update_signature_is_frozen():
    assert _params(TaskRepo.get_for_update) == [
        ("self", "POSITIONAL_OR_KEYWORD"), ("task_id", "POSITIONAL_OR_KEYWORD"),
        ("expected_version", "POSITIONAL_OR_KEYWORD")]


def test_ai_client_interface_is_frozen():
    """契約擁有者為 Dev-B；凍結後由 Dev-B 維護本測試。"""
    assert _params(AIClient.call) == [("self", "POSITIONAL_OR_KEYWORD"), ("node_id", "POSITIONAL_OR_KEYWORD"),
                                      ("payload", "POSITIONAL_OR_KEYWORD"), ("timeout_s", "KEYWORD_ONLY")]
    assert _params(AIClient.health) == [("self", "POSITIONAL_OR_KEYWORD")]


def test_error_codes_match_spec_table():
    section = SPEC.read_text(encoding="utf-8").split("### 5.2 錯誤碼", 1)[1].split("### 5.3", 1)[0]
    in_spec = {code: int(status) for status, code in re.findall(r"^\| (\d{3}) \| `([A-Z_]+)` \|", section, re.M)}
    assert in_spec == ERROR_STATUS
