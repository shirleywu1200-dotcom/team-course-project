#!/usr/bin/env bash
# 讓 git 使用 repo 內的 hooks（需在 git init 之後執行一次）。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath scripts/hooks
echo "已設定 core.hooksPath=scripts/hooks"
