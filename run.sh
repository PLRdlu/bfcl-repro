# BFCL 本地复现 —— 一键跑分脚本（Git Bash）
#
# 用法：
#   ./run.sh                       # 跑全部 5 个类别（默认，正式交付口径，约 21 分钟）
#   ./run.sh ab                    # 只跑 A+B 两组（跳过耗时的多轮，约 12 分钟）
#   ./run.sh simple_python         # 只跑指定类别（可逗号分隔多个）
#   ./run.sh evaluate-only         # 只重跑评估，不重新生成（不消耗 API）
#
# 关键约定：
#   BFCL_PROJECT_ROOT 必须是 Windows 风格路径（D:/... 或 C:/...）。
#   Git Bash 的 $PWD 是 /d/... 形式，Python 会解析成 \d\... 导致 .env 找不到，
#   所以这里统一用 `pwd -W` 取 Windows 路径。
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
# D:/bfcl-venv 是指向 D:/py项目uv环境/bfcl/.venv3 的 junction（ASCII 路径，
# 方便绕开 Windows 编码问题）；换机器时用 BFCL_PYTHON 覆盖即可。
BFCL_PYTHON="${BFCL_PYTHON:-D:/bfcl-venv/Scripts/python.exe}"
MODEL="${BFCL_MODEL:-DeepSeek-V4.1-Flash-FC}"
THREADS="${BFCL_THREADS:-8}"

export BFCL_PROJECT_ROOT="$PROJECT_ROOT"

# A 组：单函数调用（主分）
GROUP_A="simple_python"
# B 组：工具调用判断力（该不该调）
GROUP_B="irrelevance,live_irrelevance,live_relevance"
# C 组：多轮有状态（最难，占 Overall 权重 30%）
GROUP_C="multi_turn_base"

usage() {
    sed -n '2,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

run_generate() {
    local cats="$1"
    echo ">>> generate [$MODEL] categories=$cats threads=$THREADS"
    "$BFCL_PYTHON" tools/bfcl_cli.py generate \
        --model "$MODEL" \
        --test-category "$cats" \
        --num-threads "$THREADS"
}

run_evaluate() {
    local cats="$1"
    echo ">>> evaluate [$MODEL] categories=$cats"
    # --partial-eval：允许只评估已有结果文件的子集（生成中断时必备）
    "$BFCL_PYTHON" tools/bfcl_cli.py evaluate \
        --model "$MODEL" \
        --test-category "$cats" \
        --partial-eval
}

ALL="$GROUP_A,$GROUP_B,$GROUP_C"

case "${1:-all}" in
    all)
        run_generate "$GROUP_A"
        run_generate "$GROUP_B"
        run_generate "$GROUP_C"
        # 评估一次性聚合 5 个类别，否则 Overall 表会只剩最后一次的类别
        run_evaluate "$ALL"
        ;;
    ab)
        run_generate "$GROUP_A"
        run_generate "$GROUP_B"
        run_evaluate "$GROUP_A,$GROUP_B"
        ;;
    evaluate-only)
        run_evaluate "$ALL"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        run_generate "$1"
        run_evaluate "$1"
        ;;
esac

echo
echo "=== 分数总表：$PROJECT_ROOT/score/data_overall.csv ==="
cat "$PROJECT_ROOT/score/data_overall.csv" 2>/dev/null || true
