"""R1 規則（FR-INB-02、AC-42）：LINE 群組未綁定或未告知成員，訊息一律丟棄、不存原文。

webhook（todo 7.12）本版不做；這個函式留給之後的 webhook 在寫入 sources 之前呼叫。
"""


def accept_line_message(group: dict | None) -> bool:
    return group is not None and bool(group["notified"]) and bool(group["bound"])
