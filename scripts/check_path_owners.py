#!/usr/bin/env python3
"""檢查 PR 作者是否為所修改受保護路徑的負責人（todo 6.2；選項 C 的自動防線）。

用法：check_path_owners.py <PR 作者帳號> < 變更檔案清單（每行一個路徑）
規則檔：.github/path-owners.txt。違規時以非 0 結束並列出檔案；未設定負責人的路徑只提示。
"""

import sys
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parents[1] / ".github" / "path-owners.txt"


def load_rules(text: str) -> list[tuple[str, set[str]]]:
    rules = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        prefix, *owners = line.split()
        rules.append((prefix, {o.lstrip("@").lower() for o in owners}))
    return rules


def owners_for(path: str, rules: list[tuple[str, set[str]]]) -> tuple[str, set[str]] | None:
    matches = [(p, o) for p, o in rules if path == p or path.startswith(p) and p.endswith("/")]
    return max(matches, key=lambda m: len(m[0])) if matches else None


def check(author: str, paths: list[str], rules: list[tuple[str, set[str]]]) -> tuple[list[str], list[str]]:
    violations, unset = [], []
    for path in paths:
        rule = owners_for(path, rules)
        if rule is None:
            continue
        prefix, owners = rule
        if not owners:
            unset.append(f"{path}（{prefix} 尚未設定負責人）")
        elif author.lower() not in owners:
            violations.append(f"{path}（負責人：{', '.join(sorted(owners))}）")
    return violations, unset


def main() -> int:
    author = sys.argv[1]
    paths = [p.strip() for p in sys.stdin if p.strip()]
    violations, unset = check(author, paths, load_rules(RULES_FILE.read_text(encoding="utf-8")))
    for u in unset:
        print(f"提示：{u}")
    if violations:
        print(f"PR 作者 {author} 修改了不屬於自己負責的受保護路徑：")
        for v in violations:
            print(f"  - {v}")
        print("請改由負責人修改，或先取得負責人同意並由負責人提交。")
        return 1
    print("path-owners 檢查通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
