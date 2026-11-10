#!/usr/bin/env bash
# 一条命令出「终端结果截图」：渲染卡片 HTML -> Chrome 无头截图
#
# 用法：
#   bash tools/shot.sh                    # 输出 docs/终端结果截图.png
#   bash tools/shot.sh /d/out/my.png      # 指定输出路径
#   BFCL_HEIGHT=1300 bash tools/shot.sh   # 内容变多时加高窗口
#
# 依赖：本机 Chrome（路径可用 BFCL_CHROME 覆盖）。
# 注意：--window-size 的高度太小会把表格截断，默认 1120 是实测够用的值。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
ROOT="$(cd "$HERE/.." && pwd -W)"

PY="${BFCL_PYTHON:-D:/bfcl-venv/Scripts/python.exe}"
CHROME="${BFCL_CHROME:-C:/Program Files/Google/Chrome/Application/chrome.exe}"
HEIGHT="${BFCL_HEIGHT:-1120}"
WIDTH="${BFCL_WIDTH:-1280}"
OUT="${1:-$ROOT/docs/终端结果截图.png}"

if [ ! -x "$PY" ] && [ ! -f "$PY" ]; then
    echo "[ERR] 找不到解释器: $PY" >&2
    exit 1
fi
if [ ! -f "$CHROME" ]; then
    echo "[ERR] 找不到 Chrome: $CHROME（用 BFCL_CHROME=... 指定）" >&2
    exit 1
fi

# 1) 从 run_full.log + score/*.csv 渲染卡片（数字不手填）
"$PY" "$ROOT/tools/make_result_card.py"

# 2) 无头截图（Chrome 会直接覆盖同名文件，不要先删——本机沙箱可能拦删除）
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-first-run \
    --user-data-dir="$TEMP/chrome_bfcl" \
    --window-size="${WIDTH},${HEIGHT}" \
    --screenshot="$(cygpath -w "$OUT" 2>/dev/null || echo "$OUT")" \
    "file:///$(cygpath -m "$ROOT/docs/_result_card.html" 2>/dev/null || echo "$ROOT/docs/_result_card.html")" \
    2>&1 | tail -2

if [ -f "$OUT" ]; then
    echo "[OK] $OUT  ($(wc -c < "$OUT") bytes)"
else
    echo "[ERR] 截图未生成" >&2
    exit 1
fi
