"""「可對外任務」共用判斷（todo 13.9；spec 5.3a〈AI-03〉；#93 第 3 題 B）。

可對外＝任務範圍是工作，且沒有專案或專案範圍是工作。專案封存與否不是輸入（只看 scope）。
這是純函式的真值表；送 AI 時的行為由 tests/acceptance/test_issue93_shareable_tasks.py 驗證。
"""

import pytest

from app.domain.shareable import is_shareable


@pytest.mark.parametrize(("task_scope", "project_scope", "expected"), [
    ("work", None, True),
    ("work", "work", True),
    ("work", "private", False),
    ("private", None, False),
    ("private", "work", False),
    ("private", "private", False),
])
def test_u1_truth_table(task_scope, project_scope, expected):
    assert is_shareable(task_scope, project_scope) is expected
