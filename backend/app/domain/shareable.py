"""「可對外任務」：可以送給 AI 的任務（spec 5.3a〈AI-03〉；#93 第 3 題 B，todo 13.9；資安規則 2）。

可對外＝任務範圍是工作，且沒有專案或專案範圍是工作。專案封存與否不影響。
呼叫端以送出當下讀到的 tasks.scope 與 projects.scope 判定（延續 FR-INB-08a）。
AI-01、AI-03、AI-05 共用這一份；查詢任務時 LEFT JOIN projects 帶出 project_scope（無專案為 None）。
"""


def is_shareable(task_scope: str, project_scope: str | None) -> bool:
    return task_scope == "work" and project_scope in (None, "work")
